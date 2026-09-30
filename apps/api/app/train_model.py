"""Reproducible operational demo comparison on synthetic seed only."""

from sqlalchemy import select
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from .core import SessionLocal
from .models import ModelRegistry, Occurrence


def train():
    with SessionLocal() as db:
        rows = db.scalars(
            select(Occurrence).where(Occurrence.deleted_at.is_(None))
        ).all()
        if len(rows) < 20:
            return
        priorities = {"Baixa": 0, "Média": 1, "Alta": 2, "Crítica": 3}
        features = [
            [
                priorities.get(o.priority, 1),
                int(o.status != "Concluída"),
                int(o.latitude is None),
                min(365, max(0, (o.created_at.date() - o.occurred_at.date()).days)),
            ]
            for o in rows
        ]
        target = [int(o.risk_score >= 70) for o in rows]
        x_train, x_test, y_train, y_test = train_test_split(
            features, target, test_size=0.3, random_state=2026, stratify=target
        )
        results = {}
        for name, model in (
            ("majority_baseline", DummyClassifier(strategy="most_frequent")),
            ("logistic_regression", LogisticRegression(max_iter=300)),
            (
                "random_forest",
                RandomForestClassifier(n_estimators=50, random_state=2026),
            ),
        ):
            model.fit(x_train, y_train)
            predictions = model.predict(x_test)
            results[name] = {
                "accuracy": round(accuracy_score(y_test, predictions), 3),
                "f1": round(f1_score(y_test, predictions, zero_division=0), 3),
            }
            if name == "random_forest":
                results[name]["feature_importance"] = dict(
                    zip(
                        ("priority", "open", "missing_coordinates", "elapsed_days"),
                        [round(float(v), 3) for v in model.feature_importances_],
                    )
                )
        row = db.scalar(
            select(ModelRegistry).where(
                ModelRegistry.name == "SyntheticPriorityComparison"
            )
        )
        if not row:
            row = ModelRegistry(
                name="SyntheticPriorityComparison",
                version="1",
                card="Classificação experimental de prioridade operacional em 50 registros sintéticos. Split estratificado 70/30. Rótulos derivados do escore por regras; resultado não mede desempenho epidemiológico nem generalização. Proibido para decisão real.",
            )
            db.add(row)
        row.metrics = results
        db.commit()


if __name__ == "__main__":
    train()
