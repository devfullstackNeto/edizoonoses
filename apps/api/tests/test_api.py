import io
import time
from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings

client = TestClient(app)


def auth(email="admin@demo.local", password=None):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password or settings.demo_password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_login_rbac_and_occurrence_lifecycle():
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@demo.local", "password": "wrong"},
        ).status_code
        == 401
    )
    viewer = auth("viewer@demo.local")
    assert (
        client.post("/api/v1/occurrences", headers=viewer, json={}).status_code == 403
    )
    admin = auth()
    body = {
        "type": "Morcego",
        "description": "Ocorrência sintética de teste",
        "territory": "Centro Demo",
        "address": "Rua de teste 1",
        "latitude": -15.58,
        "longitude": -56.09,
    }
    created = client.post("/api/v1/occurrences", headers=admin, json=body)
    assert created.status_code == 201, created.text
    oid = created.json()["id"]
    assert created.json()["protocol"].startswith("DEMO-")
    assert client.get(f"/api/v1/occurrences/{oid}", headers=admin).json()["timeline"]
    assert (
        client.patch(
            f"/api/v1/occurrences/{oid}", headers=admin, json={"status": "Concluída"}
        ).status_code
        == 200
    )
    geo = client.get("/api/v1/map/features", headers=admin).json()
    assert any(f["properties"]["id"] == oid for f in geo["features"])
    territory_geo = client.get("/api/v1/territories.geojson", headers=admin).json()
    assert territory_geo["type"] == "FeatureCollection"
    assert len(territory_geo["features"]) >= 5
    dashboard = client.get("/api/v1/dashboard", headers=admin).json()
    assert dashboard["total"] >= 51
    assert client.delete(f"/api/v1/occurrences/{oid}", headers=admin).status_code == 200
    assert client.get(f"/api/v1/occurrences/{oid}", headers=admin).status_code == 404
    assert any(
        x["entity_id"] == oid for x in client.get("/api/v1/audit", headers=admin).json()
    )


def test_document_ocr_chat_quality_and_exports():
    admin = auth()
    with open("fixtures/formulario_demo_1.png", "rb") as f:
        uploaded = client.post(
            "/api/v1/documents",
            headers=admin,
            files={"file": ("fixture.png", f, "image/png")},
            data={"classification": "Interno"},
        )
    assert uploaded.status_code == 201, uploaded.text
    doc = uploaded.json()
    assert len(doc["sha256"]) == 64
    assert (
        client.get(f"/api/v1/documents/{doc['id']}/download", headers=admin).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/documents/{doc['id']}/download", headers=auth("viewer@demo.local")
        ).status_code
        == 403
    )
    job = client.post(
        "/api/v1/ocr/jobs", headers=admin, json={"document_id": doc["id"]}
    )
    assert job.status_code == 202, job.text
    jid = job.json()["id"]
    for _ in range(30):
        result = client.get(f"/api/v1/ocr/jobs/{jid}", headers=admin).json()
        if result["status"] in ("needs_review", "failed"):
            break
        time.sleep(1)
    assert result["status"] == "needs_review", result
    assert "DEMO-OCR" in result["raw_text"]
    reviewed = client.post(
        f"/api/v1/ocr/jobs/{jid}/review",
        headers=admin,
        json={"decision": "approved", "fields": result["fields"]},
    )
    assert reviewed.status_code == 200
    grounded = client.post(
        "/api/v1/chat/messages", headers=admin, json={"text": "morcegos"}
    ).json()
    assert grounded["source_refs"] and not grounded["fallback"]
    fallback = client.post(
        "/api/v1/chat/messages",
        headers=admin,
        json={"text": "telefone oficial de uma cidade desconhecida"},
    ).json()
    assert fallback["fallback"]
    assert (
        client.post("/api/v1/quality/scan", headers=admin, json={}).status_code == 200
    )
    assert (
        client.get("/api/v1/export/occurrences.geojson", headers=admin).json()["type"]
        == "FeatureCollection"
    )


def test_csv_transaction():
    admin = auth()
    csv_bytes = b"type,description,address,latitude,longitude,territory,status,priority\nMorcego,Registro importado,Rua Sintetica 1,-15.58,-56.09,Centro Demo,Pendente,Media\n"
    preview = client.post(
        "/api/v1/import/preview",
        headers=admin,
        files={"file": ("demo.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    sha = preview.json()["sha256"]
    committed = client.post(
        "/api/v1/import/commit",
        headers=admin,
        files={"file": ("demo.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"sha256": sha},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["imported"] == 1


def test_route_order_and_visit():
    admin = auth()
    rows = client.get("/api/v1/occurrences?page_size=3", headers=admin).json()["items"]
    created = client.post(
        "/api/v1/routes",
        headers=admin,
        json={
            "name": "Rota teste sintética",
            "occurrence_ids": [r["id"] for r in rows],
        },
    )
    assert created.status_code == 200, created.text
    route = created.json()
    assert len(route["stops"]) == 3
    assert route["provider"] in ("local", "osrm")
    assert len(route["geometry"]) >= 3
    assert len(route["legs_km"]) == 2
    assert abs(sum(route["legs_km"]) - route["total_km"]) < 0.1
    order = [s["id"] for s in reversed(route["stops"])]
    updated = client.patch(
        f"/api/v1/routes/{route['id']}", headers=admin, json={"order": order}
    ).json()
    assert [s["id"] for s in updated["stops"]] == order
    visited = client.patch(
        f"/api/v1/routes/{route['id']}",
        headers=admin,
        json={"visited_stop_id": order[0]},
    ).json()
    assert visited["stops"][0]["visited"] is True
    assert visited["stops"][0]["visited_at"]


def test_pilot_fixture_ocr_link_preview_and_workspace():
    admin = auth()
    occurrence = client.get("/api/v1/occurrences?page_size=1", headers=admin).json()[
        "items"
    ][0]
    with open("fixtures/ficha_atendimento_sintetica.png", "rb") as f:
        uploaded = client.post(
            "/api/v1/documents",
            headers=admin,
            files={"file": ("ficha-piloto.png", f, "image/png")},
        )
    assert uploaded.status_code == 201, uploaded.text
    doc = uploaded.json()
    preview = client.get(f"/api/v1/documents/{doc['id']}/preview", headers=admin)
    assert preview.status_code == 200
    assert preview.headers["content-disposition"].startswith("inline")
    assert (
        client.get(
            f"/api/v1/documents/{doc['id']}/preview", headers=auth("viewer@demo.local")
        ).status_code
        == 403
    )
    job = client.post(
        "/api/v1/ocr/jobs", headers=admin, json={"document_id": doc["id"]}
    )
    assert job.status_code == 202
    for _ in range(45):
        result = client.get(
            f"/api/v1/ocr/jobs/{job.json()['id']}", headers=admin
        ).json()
        if result["status"] in ("needs_review", "failed"):
            break
        time.sleep(1)
    assert result["status"] == "needs_review", result
    assert "DEMO-OCR-PILOT-001" in result["raw_text"]
    assert result["confidence"] > 40
    review = client.post(
        f"/api/v1/ocr/jobs/{job.json()['id']}/review",
        headers=admin,
        json={
            "decision": "approved",
            "fields": result["fields"],
            "occurrence_id": occurrence["id"],
        },
    )
    assert review.status_code == 200, review.text
    workspace = client.get(
        f"/api/v1/occurrences/{occurrence['id']}/workspace", headers=admin
    ).json()
    assert any(d["id"] == doc["id"] for d in workspace["documents"])
    assert any(j["id"] == job.json()["id"] for j in workspace["ocr_jobs"])


def test_csv_column_mapping_and_invalid_route_order():
    admin = auth()
    data = b"categoria,descricao,local,lat,lon,area,situacao,urgencia\nMorcego,Registro mapeado,Rua Modelo 10,-15.58,-56.09,Centro Demo,Pendente,Media\n"
    mapping = {
        "type": "categoria",
        "description": "descricao",
        "address": "local",
        "latitude": "lat",
        "longitude": "lon",
        "territory": "area",
        "status": "situacao",
        "priority": "urgencia",
    }
    import json

    preview = client.post(
        "/api/v1/import/preview",
        headers=admin,
        files={"file": ("mapeado.csv", io.BytesIO(data), "text/csv")},
        data={"mapping": json.dumps(mapping)},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid_count"] == 1
    assert (
        client.post(
            "/api/v1/import/commit",
            headers=admin,
            files={"file": ("mapeado.csv", io.BytesIO(data), "text/csv")},
            data={
                "sha256": preview.json()["sha256"],
                "mapping": json.dumps(mapping),
                "preview_token": "wrong",
            },
        ).status_code
        == 409
    )
    committed = client.post(
        "/api/v1/import/commit",
        headers=admin,
        files={"file": ("mapeado.csv", io.BytesIO(data), "text/csv")},
        data={
            "sha256": preview.json()["sha256"],
            "mapping": json.dumps(mapping),
            "preview_token": preview.json()["preview_token"],
        },
    )
    assert committed.status_code == 200
    assert committed.json()["imported"] == 1
    routes = client.get("/api/v1/routes", headers=admin).json()
    route = next(r for r in routes if len(r["stops"]) >= 2)
    duplicate = [route["stops"][0]["id"]] * len(route["stops"])
    assert (
        client.patch(
            f"/api/v1/routes/{route['id']}", headers=admin, json={"order": duplicate}
        ).status_code
        == 422
    )


def test_role_policy_restricts_backend_permission():
    admin = auth()
    analyst = auth("analista@demo.local")
    policies = client.get("/api/v1/admin/roles", headers=admin).json()
    current = next(p for p in policies if p["name"] == "analyst")
    limited = [p for p in current["permissions"] if p != "exports:read"]
    try:
        updated = client.patch(
            "/api/v1/admin/roles/analyst", headers=admin, json={"permissions": limited}
        )
        assert updated.status_code == 200, updated.text
        assert (
            client.get("/api/v1/export/occurrences.csv", headers=analyst).status_code
            == 403
        )
        assert (
            client.get("/api/v1/export/occurrences.csv", headers=admin).status_code
            == 200
        )
    finally:
        client.patch(
            "/api/v1/admin/roles/analyst",
            headers=admin,
            json={"permissions": current["permissions"]},
        )
    assert (
        client.get("/api/v1/export/occurrences.csv", headers=analyst).status_code == 200
    )


def test_second_synthetic_ocr_fixture():
    admin = auth()
    with open("fixtures/vistoria_sintetica.png", "rb") as f:
        uploaded = client.post(
            "/api/v1/documents",
            headers=admin,
            files={"file": ("vistoria-piloto.png", f, "image/png")},
        )
    assert uploaded.status_code == 201
    job = client.post(
        "/api/v1/ocr/jobs", headers=admin, json={"document_id": uploaded.json()["id"]}
    )
    assert job.status_code == 202
    for _ in range(45):
        result = client.get(
            f"/api/v1/ocr/jobs/{job.json()['id']}", headers=admin
        ).json()
        if result["status"] in ("needs_review", "failed"):
            break
        time.sleep(1)
    assert result["status"] == "needs_review", result
    assert "DEMO-OCR-PILOT-002" in result["raw_text"]
    assert result["confidence"] > 40
