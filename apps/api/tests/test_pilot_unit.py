from types import SimpleNamespace
from app.main import OpenAICompatibleProvider
from app.routing import calculate_route
from app.settings import settings
import httpx


def test_osrm_fallback(monkeypatch):
    monkeypatch.setattr(settings, "osrm_base_url", "http://unavailable.invalid")
    monkeypatch.setattr(
        "app.routing.httpx.get",
        lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )
    points = [
        SimpleNamespace(latitude=-15.58, longitude=-56.09),
        SimpleNamespace(latitude=-15.59, longitude=-56.08),
    ]
    result = calculate_route(points)
    assert result["provider"] == "local"
    assert len(result["legs_km"]) == 1
    assert result["total_km"] > 0


def test_osrm_road_geometry_when_available(monkeypatch):
    monkeypatch.setattr(settings, "osrm_base_url", "http://osrm.local")
    points = [
        SimpleNamespace(latitude=-15.58, longitude=-56.09),
        SimpleNamespace(latitude=-15.59, longitude=-56.08),
    ]

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "routes": [
                    {
                        "distance": 2400,
                        "legs": [{"distance": 2400}],
                        "geometry": {
                            "coordinates": [
                                [-56.09, -15.58],
                                [-56.085, -15.585],
                                [-56.08, -15.59],
                            ]
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.routing.httpx.get", lambda *a, **k: Response())
    result = calculate_route(points)
    assert result["provider"] == "osrm"
    assert result["total_km"] == 2.4
    assert len(result["geometry"]) == 3


def test_optional_chat_provider_grounding_and_fallback(monkeypatch):
    item = SimpleNamespace(
        id="kb-1",
        title="Morcegos",
        tags=["morcegos"],
        body="Orientação sintética validada.",
        source="manual-demo",
        version=1,
    )
    monkeypatch.setattr(settings, "ai_base_url", "http://provider.invalid")
    monkeypatch.setattr(settings, "ai_api_key", "unit-test-key")
    monkeypatch.setattr(settings, "ai_model", "unit-test-model")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "Orientação sintética validada."}}]
            }

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("app.main.httpx.post", fake_post)
    provider = OpenAICompatibleProvider()
    answer = provider.answer("Como lidar com morcegos?", [item])
    assert answer["text"] == item.body
    assert answer["source_refs"][0]["id"] == item.id
    assert len(calls) == 1
    unknown = provider.answer("Qual o telefone de Marte?", [item])
    assert unknown["fallback"] and not unknown["source_refs"]
    assert len(calls) == 1
