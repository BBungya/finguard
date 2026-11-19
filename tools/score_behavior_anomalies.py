"""직전 카드 이력의 드문 정도를 학습하고 검증 구간별 특성을 집계한다."""

import json
from importlib.metadata import version

import joblib
import numpy as np
from cluster_behaviors import summarize
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from train_baselines import ROOT, load_periods
from tune_history_models import HISTORY_COLUMNS, history_inputs, read_settings


def main():
    settings = read_settings("behavior_anomalies.toml")
    train, validation, _ = load_periods(read_settings("ml_split.toml"))
    histories = history_inputs((train, validation))
    print("Computing train history", flush=True)
    train_history = next(histories)
    train_known = train_history[:, 1] > 0
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(np.log1p(train_history[train_known]))
    model = IsolationForest(
        n_estimators=settings["n_estimators"],
        max_samples=settings["max_samples"],
        contamination="auto",
        random_state=settings["seed"],
        n_jobs=settings["workers"],
    )
    with threadpool_limits(limits=settings["workers"]):
        model.fit(train_scaled)
    # sklearn은 값이 작을수록 이상하다. 부호를 바꿔 큰 값이 더 드물게 한다.
    print("Scoring train history", flush=True)
    train_scores = -model.score_samples(train_scaled)
    boundaries = np.quantile(train_scores, settings["score_quantiles"])
    train_bands = np.full(len(train), -1, dtype=int)
    train_bands[train_known] = np.searchsorted(boundaries, train_scores, side="right")
    results = {
        "seed": settings["seed"],
        "sklearn": version("scikit-learn"),
        "history_columns": list(HISTORY_COLUMNS),
        "training_rows_with_history": int(train_known.sum()),
        "score_quantiles": settings["score_quantiles"],
        "score_boundaries": boundaries.tolist(),
        "train_score_min": float(train_scores.min()),
        "train_score_max": float(train_scores.max()),
        "train": summarize(train, train_history, train_bands),
    }

    print("Computing and scoring validation history", flush=True)
    validation_history = next(histories)
    validation_known = validation_history[:, 1] > 0
    validation_scores = -model.score_samples(
        scaler.transform(np.log1p(validation_history[validation_known]))
    )
    validation_bands = np.full(len(validation), -1, dtype=int)
    validation_bands[validation_known] = np.searchsorted(
        boundaries, validation_scores, side="right"
    )
    results["validation"] = summarize(validation, validation_history, validation_bands)
    results["validation_score_min"] = float(validation_scores.min())
    results["validation_score_max"] = float(validation_scores.max())
    output = ROOT / "artifacts/behavior_anomalies"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"scaler": scaler, "isolation_forest": model, "score_boundaries": boundaries},
        output / "anomaly_model.joblib",
    )
    (output / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(output / "results.json")


if __name__ == "__main__":
    main()
