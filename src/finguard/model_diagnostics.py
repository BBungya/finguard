"""조사 대상의 오류, 점수 신뢰도, 모델 계산 비용을 요약한다."""

from io import BytesIO
from itertools import pairwise
from time import perf_counter_ns

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss
from threadpoolctl import threadpool_limits

from finguard.baseline_metrics import daily_rank, outcome, select_daily

SCORE_CUTS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5, 0.8)


def calibration(labels, scores):
    scores = np.asarray(scores, dtype=np.float64)
    groups = np.searchsorted(SCORE_CUTS, scores, side="right")
    intervals = (0.0, *SCORE_CUTS, 1.0)
    bins = []
    for index, (lower, upper) in enumerate(pairwise(intervals)):
        mask = groups == index
        if not mask.any():
            continue
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "count": int(mask.sum()),
                "mean_score": float(scores[mask].mean()),
                "fraud_rate": float(labels[mask].mean()),
            }
        )
    # ECE는 각 구간의 점수-관측 비율 차이를 구간의 거래 건수로 가중평균한다.
    ece = sum(b["count"] * abs(b["mean_score"] - b["fraud_rate"]) for b in bins) / len(
        labels
    )
    return {"brier": float(brier_score_loss(labels, scores)), "ece": ece, "bins": bins}


def subgroup_errors(frame, scores, daily_budget, unseen_cards):
    labels = frame["is_fraud"].to_numpy()
    chosen = select_daily(daily_rank(frame, scores), daily_budget)
    groups = {
        "hour": pd.cut(
            frame["trans_date_trans_time"].dt.hour,
            [0, 6, 12, 18, 24],
            labels=["00–05", "06–11", "12–17", "18–23"],
            right=False,
        ),
        "amount": pd.cut(
            frame["amt"],
            [0, 50, 200, 500, np.inf],
            labels=["<50", "50–<200", "200–<500", "≥500"],
            right=False,
        ),
        "card": np.where(frame["cc_num"].isin(unseen_cards), "unseen", "seen"),
    }
    # 일일 상위 거래를 먼저 고른 뒤 나누어야 구간마다 조사 한도가 늘어나지 않는다.
    return {
        dimension: {
            str(value): outcome(labels[mask], chosen[mask])
            for value in pd.unique(values)
            if (mask := np.asarray(values == value)).any()
        }
        for dimension, values in groups.items()
    }


def measure_model(model, features, sample_size=200):
    indices = np.linspace(0, features.shape[0] - 1, sample_size, dtype=int)
    rows = [features[index] for index in indices]
    duration_ms = []
    workers = model.n_jobs
    model.set_params(n_jobs=1)
    try:
        with threadpool_limits(limits=1):
            for row in rows[:10]:
                model.predict_proba(row)
            for row in rows:
                start = perf_counter_ns()
                model.predict_proba(row)
                duration_ms.append((perf_counter_ns() - start) / 1_000_000)
    finally:
        model.set_params(n_jobs=workers)
    if isinstance(model, RandomForestClassifier):
        nodes = sum(tree.tree_.node_count for tree in model.estimators_)
    else:
        nodes = len(model.get_booster().trees_to_dataframe())
    artifact = BytesIO()
    joblib.dump(model, artifact)
    return {
        "trees": model.n_estimators,
        "max_depth": model.max_depth,
        "nodes": nodes,
        "model_bytes": artifact.tell(),
        "scored_rows": sample_size,
        "median_ms": float(np.median(duration_ms)),
        "p95_ms": float(np.percentile(duration_ms, 95)),
    }
