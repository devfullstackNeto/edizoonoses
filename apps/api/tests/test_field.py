import time
from app.settings import settings
from test_api import auth, client


def test_field_journey_geofence_evidence_ocr_and_privacy():
    admin, viewer = auth(), auth("viewer@demo.local")
    address = client.get(
        "/api/v1/geocode/search?q=Rua%20Sint%C3%A9tica%201", headers=admin
    )
    assert address.status_code == 200, address.text
    assert address.json()["items"]
    assert client.get("/api/v1/geocode/search?q=a", headers=admin).status_code == 422
    occurrence = client.post(
        "/api/v1/occurrences",
        headers=admin,
        json={
            "type": "Morcego",
            "description": "Visita sintética da Sprint 3",
            "address": "Rua Teste Campo, 100",
            "territory": "Centro Demo",
            "latitude": -15.58,
            "longitude": -56.09,
        },
    )
    assert occurrence.status_code == 201, occurrence.text
    oid = occurrence.json()["id"]
    route = client.post(
        "/api/v1/routes",
        headers=admin,
        json={
            "name": "Rota campo teste",
            "occurrence_ids": [oid],
            "start_latitude": -15.581,
            "start_longitude": -56.091,
        },
    )
    assert route.status_code == 200, route.text
    rid = route.json()["id"]
    assert route.json()["start_latitude"] == -15.581
    assert len(route.json()["legs_km"]) == 1
    assert (
        client.post(
            f"/api/v1/field/routes/{rid}/checkins",
            headers=admin,
            json={"latitude": -15.58, "longitude": -56.09},
        ).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/field/routes/{rid}/start", headers=viewer).status_code
        == 403
    )
    started = client.post(f"/api/v1/field/routes/{rid}/start", headers=admin)
    assert started.status_code == 200, started.text
    vid = started.json()["visits"][0]["id"]
    outside = client.post(
        f"/api/v1/field/visits/{vid}/arrive",
        headers=admin,
        json={"latitude": -15.60, "longitude": -56.09},
    )
    assert (
        outside.status_code == 200
        and outside.json()["checkin"]["decision"] == "outside"
    )
    assert outside.json()["visit"]["status"] == "pending"
    assert (
        client.post(
            f"/api/v1/field/visits/{vid}/arrive",
            headers=admin,
            json={"manual_override": True, "justification": "curta"},
        ).status_code
        == 422
    )
    manual = client.post(
        f"/api/v1/field/visits/{vid}/arrive",
        headers=admin,
        json={
            "manual_override": True,
            "justification": "Endereço conferido manualmente",
        },
    )
    assert (
        manual.status_code == 200 and manual.json()["checkin"]["decision"] == "override"
    )
    arrival = client.post(
        f"/api/v1/field/visits/{vid}/arrive",
        headers=admin,
        json={"latitude": -15.58, "longitude": -56.09},
    )
    assert (
        arrival.status_code == 200 and arrival.json()["checkin"]["decision"] == "inside"
    )
    assert (
        client.post(f"/api/v1/field/visits/{vid}/start", headers=admin).status_code
        == 200
    )
    issue = client.post(
        f"/api/v1/field/visits/{vid}/issues",
        headers=admin,
        json={"title": "Requer revisita sintética", "severity": "Alta"},
    )
    assert issue.status_code == 201, issue.text
    assert (
        client.patch(
            f"/api/v1/field/issues/{issue.json()['id']}",
            headers=admin,
            json={"status": "resolved"},
        ).status_code
        == 200
    )
    with open("fixtures/dossie_visita_sintetico.pdf", "rb") as f:
        uploaded = client.post(
            "/api/v1/documents",
            headers=admin,
            files={"file": ("dossie_visita_sintetico.pdf", f, "application/pdf")},
            data={"classification": "Interno", "visit_id": vid},
        )
    assert uploaded.status_code == 201, uploaded.text
    did = uploaded.json()["id"]
    assert uploaded.json()["occurrence_id"] == oid
    job = client.post("/api/v1/ocr/jobs", headers=admin, json={"document_id": did})
    assert job.status_code == 202, job.text
    jid = job.json()["id"]
    for _ in range(90):
        result = client.get(f"/api/v1/ocr/jobs/{jid}", headers=admin).json()
        if result["status"] in ("needs_review", "failed"):
            break
        time.sleep(1)
    assert result["status"] == "needs_review", result
    assert len(result["pages"]) == 2
    assert all(p["raw_text"] for p in result["pages"])
    assert result["field_details"]
    fields = dict(result["fields"])
    fields["revisado_manualmente"] = "sim"
    approved = client.post(
        f"/api/v1/ocr/jobs/{jid}/review",
        headers=admin,
        json={"decision": "approved", "fields": fields, "occurrence_id": oid},
    )
    assert approved.status_code == 200, approved.text
    assert any(f["status"] == "added" for f in approved.json()["field_details"])
    assert (
        client.get("/api/v1/documents?search=DEMO-OCR", headers=admin).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/field/visits/{vid}/finish",
            headers=admin,
            json={"outcome": "requer revisita", "observation": "Registro sintético"},
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/field/routes/{rid}/finish", headers=admin).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/field/routes/{rid}/checkins",
            headers=admin,
            json={"latitude": -15.58, "longitude": -56.09},
        ).status_code
        == 409
    )
    assert (
        client.get(f"/api/v1/field/routes/{rid}/checkins", headers=viewer).status_code
        == 403
    )
    assert client.get(f"/api/v1/ocr/jobs/{jid}", headers=viewer).status_code == 403
    timeline = client.get(f"/api/v1/occurrences/{oid}", headers=admin).json()[
        "timeline"
    ]
    actions = {event["action"] for event in timeline}
    assert {
        "route_planned",
        "route_started",
        "arrival_confirmed",
        "visit_started",
        "document_uploaded",
        "ocr_reviewed",
        "visit_completed",
        "route_finished",
    } <= actions
    dashboard = client.get("/api/v1/dashboard", headers=admin).json()["field"]
    assert dashboard["visits_completed"] >= 1
    assert settings.location_retention_days >= 1
