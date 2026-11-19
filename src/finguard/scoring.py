"""저장된 모델로 점수를 계산하고 성공한 거래를 이력에 반영한다."""

import hashlib
import math
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from finguard.features import HistoryFeatureCalculator, HistoryFeatures
from finguard.model_inputs import add_history, behavior_values, inputs, variant_inputs
from finguard.transactions import Transaction

POLICY_VERSION = "fixed-threshold-v1"


@dataclass(frozen=True)
class ScoreResult:
    transaction_id: str
    risk_score: float
    review_required: bool
    threshold: float | None
    cluster_id: int
    model_version: str
    policy_version: str
    features: HistoryFeatures


class ScoringModel:
    def __init__(self, path: Path):
        with path.open("rb") as source:
            self.version = hashlib.file_digest(source, "sha256").hexdigest()
        self.bundle = joblib.load(path)
        required = {
            "preprocessor",
            "scaler",
            "cluster",
            "anomaly",
            "xgboost",
            "variant",
            "threshold",
        }
        if not required.issubset(self.bundle) or self.bundle["variant"] not in {
            "baseline",
            "cluster",
            "anomaly",
            "both",
        }:
            raise ValueError("unsupported_scoring_bundle")
        self.threshold = self.bundle["threshold"]
        if self.threshold is not None and (
            not math.isfinite(self.threshold) or not 0 <= self.threshold <= 1
        ):
            raise ValueError("invalid_model_threshold")

    def predict(
        self, transaction: Transaction, features: HistoryFeatures
    ) -> tuple[float, int]:
        rows = pd.DataFrame(
            {
                "amt": [float(transaction.amount)],
                "trans_date_trans_time": [pd.Timestamp(transaction.occurred_at)],
                "category": [transaction.category],
            }
        )
        history = np.array(
            [
                [
                    features.count_1h,
                    features.count_7d,
                    features.mean_amount_7d
                    if features.mean_amount_7d is not None
                    else -1,
                    features.std_amount_7d
                    if features.std_amount_7d is not None
                    else -1,
                ]
            ],
            dtype=np.float32,
        )
        groups, membership, scores = behavior_values(
            history,
            self.bundle["scaler"],
            self.bundle["cluster"],
            self.bundle["anomaly"],
            include_anomaly=self.bundle["variant"] in {"anomaly", "both"},
        )
        base = add_history(self.bundle["preprocessor"].transform(inputs(rows)), history)
        model_input = variant_inputs(base, membership, scores, self.bundle["variant"])
        risk_score = float(self.bundle["xgboost"].predict_proba(model_input)[0, 1])
        if not math.isfinite(risk_score) or not 0 <= risk_score <= 1:
            raise ValueError("invalid_model_score")
        return risk_score, int(groups[0])


class TransactionConflict(ValueError):
    pass


class ScoringUnavailable(RuntimeError):
    pass


class InMemoryScoringService:
    """단일 프로세스의 로컬 검증용 상태. DB 연결은 후속 단계에서 구현한다."""

    def __init__(self, model):
        self.model = model
        self._histories = {}
        self._results = {}
        self._lock = Lock()

    def score(self, transaction: Transaction) -> ScoreResult:
        with self._lock:
            existing = self._results.get(transaction.transaction_id)
            if existing is not None:
                previous, result = existing
                if previous != transaction:
                    raise TransactionConflict("transaction_id_payload_conflict")
                return result

            candidate = deepcopy(
                self._histories.get(transaction.card_id, HistoryFeatureCalculator())
            )
            try:
                features = candidate.process(transaction)
            except ValueError as error:
                raise TransactionConflict(str(error)) from error
            try:
                # 한 건 요청에서 과도한 계산 스레드를 만들지 않도록 제한한다.
                with threadpool_limits(limits=1):
                    score, group = self.model.predict(transaction, features)
                result = ScoreResult(
                    transaction_id=transaction.transaction_id,
                    risk_score=score,
                    review_required=self.model.threshold is not None
                    and score >= self.model.threshold,
                    threshold=self.model.threshold,
                    cluster_id=group,
                    model_version=self.model.version,
                    policy_version=POLICY_VERSION,
                    features=features,
                )
            except Exception as error:
                raise ScoringUnavailable("scoring_failed") from error
            # 점수 계산까지 성공하면 이력과 재전송용 응답을 함께 확정한다.
            self._histories[transaction.card_id] = candidate
            self._results[transaction.transaction_id] = (transaction, result)
            return result
