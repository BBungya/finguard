"""직전 거래 이력으로 비슷한 행동을 묶고, 그룹별 특성을 집계한다."""

import json
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from train_baselines import ROOT, load_periods
from tune_history_models import HISTORY_COLUMNS, history_inputs, read_settings


def summarize(frame, history, assignments):
    rows = pd.DataFrame(history, columns=HISTORY_COLUMNS)
    rows["cluster"] = assignments
    rows["card_id"] = frame["cc_num"].to_numpy()
    rows["fraud"] = frame["is_fraud"].to_numpy()
    groups = {}
    for cluster, group in rows.groupby("cluster", sort=True):
        groups[str(int(cluster))] = {
            "rows": len(group),
            "cards": group["card_id"].nunique(),
            "fraud": int(group["fraud"].sum()),
            "fraud_rate": float(group["fraud"].mean()),
            "history_medians": {
                name: float(group[name].median()) for name in HISTORY_COLUMNS
            },
        }
    return groups


def main():
    settings = read_settings("behavior_clusters.toml")
    train, validation, _ = load_periods(read_settings("ml_split.toml"))
    # 같은 카드도 거래 시점마다 이력이 달라져 다른 그룹에 배정될 수 있다.
    histories = history_inputs((train, validation))
    print("Computing training history", flush=True)
    train_history = next(histories)
    train_known = train_history[:, 1] > 0
    # 이력이 없는 상태(-1)는 별도 그룹으로 다루어 평균·표준편차에 섞지 않는다.
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(np.log1p(train_history[train_known]))
    random = np.random.default_rng(settings["seed"])
    sample = random.choice(
        len(train_scaled),
        min(settings["silhouette_sample_size"], len(train_scaled)),
        replace=False,
    )
    results = {
        "seed": settings["seed"],
        "sklearn": version("scikit-learn"),
        "history_columns": list(HISTORY_COLUMNS),
        "training_rows_with_history": int(train_known.sum()),
        "silhouette_sample_size": len(sample),
        "candidates": {},
    }
    models = {}
    with threadpool_limits(limits=settings["workers"]):
        for count in settings["cluster_counts"]:
            print(f"Fitting KMeans k={count}", flush=True)
            model = KMeans(
                n_clusters=count,
                random_state=settings["seed"],
                n_init=settings["n_init"],
            ).fit(train_scaled)
            score = silhouette_score(train_scaled[sample], model.labels_[sample])
            results["candidates"][str(count)] = {
                "silhouette": float(score),
                "inertia": float(model.inertia_),
            }
            models[count] = model
    # 그룹의 분리 정도로 선택한다. 사기 라벨은 그룹을 정한 뒤 집계할 때 쓴다.
    selected = max(
        models, key=lambda count: results["candidates"][str(count)]["silhouette"]
    )
    results["selected_cluster_count"] = selected
    model = models[selected]
    train_clusters = np.full(len(train), -1, dtype=int)
    train_clusters[train_known] = model.labels_
    results["train"] = summarize(train, train_history, train_clusters)

    print("Assigning validation history to fixed groups", flush=True)
    validation_history = next(histories)
    validation_known = validation_history[:, 1] > 0
    validation_clusters = np.full(len(validation), -1, dtype=int)
    validation_clusters[validation_known] = model.predict(
        scaler.transform(np.log1p(validation_history[validation_known]))
    )
    results["validation"] = summarize(
        validation, validation_history, validation_clusters
    )
    output = ROOT / "artifacts/behavior_clusters"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "kmeans": model}, output / "cluster_model.joblib")
    (output / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(output / "results.json")


if __name__ == "__main__":
    main()
