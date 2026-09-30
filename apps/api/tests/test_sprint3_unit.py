from types import SimpleNamespace
from app.core import nearest_neighbor
from app.geocoding import NominatimProvider
from app.routing import calculate_route
from app.worker import parse_fields


def test_route_start_changes_first_stop_and_fallback(monkeypatch):
    monkeypatch.setattr("app.routing.settings.osrm_base_url", "")
    points = [
        SimpleNamespace(id="far", latitude=-15.60, longitude=-56.10),
        SimpleNamespace(id="near", latitude=-15.58, longitude=-56.09),
    ]
    ordered, _ = nearest_neighbor(points, (-15.58, -56.09))
    assert ordered[0].id == "near"
    result = calculate_route(ordered, (-15.58, -56.09))
    assert result["provider"] == "local"
    assert len(result["legs_km"]) == 2
    assert result["geometry"][0] == [-56.09, -15.58]


def test_geocoder_adapter_and_label_parser(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "display_name": "Rua Demo, Cuiabá",
                    "lat": "-15.58",
                    "lon": "-56.09",
                    "osm_type": "way",
                    "osm_id": 12,
                }
            ]

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("app.geocoding.httpx.get", fake_get)
    item = NominatimProvider("https://self-hosted.example", "EDI-test").search(
        "Rua Demo"
    )[0]
    assert item["latitude"] == -15.58 and item["source"] == "nominatim"
    assert calls[0][1]["headers"]["User-Agent"] == "EDI-test"
    assert parse_fields(
        "Protocolo: DEMO-OCR-001\nEndereço: Rua Sintética 1\nData:\n29/09/2026"
    ) == {
        "protocolo": "DEMO-OCR-001",
        "endereco": "Rua Sintética 1",
        "data": "29/09/2026",
    }
