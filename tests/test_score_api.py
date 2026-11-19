from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from fastapi.testclient import TestClient

from finguard.api import create_app
from finguard.scoring import InMemoryScoringService
from finguard.transactions import Transaction


class ExampleModel:
    version = "test-model"
    threshold = 0.1

    def __init__(self):
        self.calls = 0
        self.fail = False

    def predict(self, transaction, features):
        self.calls += 1
        if self.fail:
            raise RuntimeError("temporary model failure")
        return features.count_7d / 10, -1


def payload(identifier="first", time="2026-01-01 10:00:00", **overrides):
    return {
        "transaction_id": identifier,
        "card_id": "0001",
        "occurred_at": time,
        "amount": "10.00",
        "category": "food_dining",
        **overrides,
    }


def test_scores_use_previous_history_and_duplicates_return_original_result():
    model = ExampleModel()
    with TestClient(create_app(model)) as client:
        first = client.post("/transactions/score", json=payload())
        second = client.post("/transactions/score", json=payload("second"))
        duplicate = client.post("/transactions/score", json=payload(amount="10.0"))
        assert first.status_code == second.status_code == duplicate.status_code == 200
        assert duplicate.json() == first.json()
        assert first.json()["features"]["count_7d"] == 0
        assert first.json()["features"]["mean_amount_7d"] is None
        assert second.json()["features"]["count_7d"] == 1
        assert Decimal(second.json()["features"]["mean_amount_7d"]) == Decimal(10)
        assert second.json()["review_required"] is True
        assert second.json()["model_version"] == "test-model"
        assert model.calls == 2

        conflict = client.post("/transactions/score", json=payload(amount="11.00"))
        assert conflict.status_code == 409
        older = client.post(
            "/transactions/score", json=payload("older", "2026-01-01 09:00:00")
        )
        assert older.status_code == 409
        other = client.post(
            "/transactions/score", json=payload("other", card_id="0002")
        )
        assert other.json()["features"]["count_7d"] == 0
        assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": "0"},
        {"amount": "NaN"},
        {"amount": "10.001"},
        {"occurred_at": "2026-02-30 10:00:00"},
        {"occurred_at": "2026-01-01T10:00:00Z"},
        {"card_id": " "},
        {"is_fraud": 1},
    ],
)
def test_invalid_requests_do_not_enter_history(overrides):
    model = ExampleModel()
    with TestClient(create_app(model)) as client:
        assert (
            client.post("/transactions/score", json=payload(**overrides)).status_code
            == 422
        )
        response = client.post("/transactions/score", json=payload())
        assert response.json()["features"]["count_7d"] == 0
        assert model.calls == 1


def test_model_failure_does_not_commit_expired_or_new_history():
    model = ExampleModel()
    with TestClient(create_app(model)) as client:
        assert client.post("/transactions/score", json=payload()).status_code == 200
        model.fail = True
        failed = client.post(
            "/transactions/score", json=payload("future", "2026-01-10 10:00:00")
        )
        assert failed.status_code == 503
        model.fail = False
        next_response = client.post(
            "/transactions/score", json=payload("second", "2026-01-01 10:30:00")
        )
        assert next_response.json()["features"]["count_7d"] == 1
        retry = client.post(
            "/transactions/score", json=payload("future", "2026-01-10 10:00:00")
        )
        assert retry.status_code == 200
        assert retry.json()["features"]["count_7d"] == 0


def test_simultaneous_duplicate_requests_commit_once():
    model = ExampleModel()
    service = InMemoryScoringService(model)
    transaction = Transaction(
        "same", datetime(2026, 1, 1, 10), "0001", "food", Decimal(10), None
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(service.score, [transaction] * 16))
    assert all(result == responses[0] for result in responses)
    assert model.calls == 1
    next_transaction = Transaction(
        "next", datetime(2026, 1, 1, 10), "0001", "food", Decimal(20), None
    )
    assert service.score(next_transaction).features.count_7d == 1
