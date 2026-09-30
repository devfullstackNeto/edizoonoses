from app.core import nearest_neighbor, risk
from app.main import chat_answer


def test_risk_is_explainable():
    score, factors = risk("Crítica", "Pendente", False)
    assert score == sum(factors.values())
    assert score >= 90


def test_route_nearest_neighbor():
    class Point:
        def __init__(self, latitude, longitude):
            self.latitude, self.longitude = latitude, longitude

    first, far, near = (
        Point(-15.58, -56.09),
        Point(-15.3, -56.0),
        Point(-15.581, -56.091),
    )
    ordered, km = nearest_neighbor([first, far, near])
    assert ordered == [first, near, far]
    assert km > 0


def test_chat_grounding_and_fallback():
    class Item:
        title = "Morcegos"
        body = "Evite contato direto."
        tags = ["morcego"]
        source = "base-demo"
        version = "1"
        id = "synthetic"

    grounded = chat_answer("Como lidar com morcego?", [Item()])
    assert grounded["text"] == Item.body
    assert grounded["source_refs"][0]["source"] == "base-demo"
    fallback = chat_answer("Qual o telefone oficial?", [Item()])
    assert fallback["fallback"] and fallback["source_refs"] == []
