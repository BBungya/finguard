"""고정한 기간으로 탐지 방식 네 가지를 학습하고 비교한다."""

import hashlib
import json
import platform
import tomllib
from importlib.metadata import version
from itertools import pairwise
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier

from finguard.baseline_metrics import choose_threshold, evaluate
from finguard.transactions import REQUIRED_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
INPUT_COLUMNS = [*sorted(REQUIRED_COLUMNS), "is_fraud"]


def load_periods(settings):
    manifest = json.loads(
        (ROOT / settings["dataset_manifest"]).read_text(encoding="utf-8")
    )
    frames = []
    for entry in manifest["files"]:
        path = ROOT / manifest["local_directory"] / entry["file"]
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != entry["sha256"]:
                raise ValueError(f"{path.name}의 SHA-256이 매니페스트와 다릅니다.")
        frames.append(
            pd.read_csv(
                path,
                usecols=INPUT_COLUMNS,
                dtype={
                    "cc_num": str,
                    "trans_num": str,
                    "amt": np.float64,
                    "is_fraud": np.int8,
                },
            )
        )
    rows = pd.concat(frames, ignore_index=True)
    times = pd.to_datetime(
        rows[settings["timestamp_column"]], format="%Y-%m-%d %H:%M:%S"
    )
    rows["trans_date_trans_time"] = times
    periods = settings["periods"]
    boundaries = [
        periods[key]
        for key in ("train_start", "validation_start", "test_start", "end_exclusive")
    ]
    parts = tuple(
        rows.loc[(times >= start) & (times < stop)]
        for start, stop in pairwise(boundaries)
    )
    if sum(map(len, parts)) != len(rows) or rows["trans_num"].duplicated().any():
        raise ValueError("기간에 속하지 않거나 거래 ID가 중복된 행이 있습니다.")
    if (
        rows.isna().any().any()
        or not rows["is_fraud"].isin([0, 1]).all()
        or not (np.isfinite(rows["amt"]) & (rows["amt"] > 0)).all()
    ):
        raise ValueError("입력값이나 사기 라벨을 확인하세요.")
    return parts


def inputs(rows):
    # 카드 번호와 정답은 모델 입력에서 제외한다. 날짜에서는 결제 당시의 시간대만 쓴다.
    return pd.DataFrame(
        {
            "log_amount": np.log1p(rows["amt"]).astype(np.float32),
            "hour": rows["trans_date_trans_time"].dt.hour,
            "category": rows["category"],
        }
    )


def main():
    settings = tomllib.loads(
        (ROOT / "configs/ml_split.toml").read_text(encoding="utf-8")
    )
    runs = tomllib.loads((ROOT / "configs/baseline.toml").read_text(encoding="utf-8"))
    train, validation, test = load_periods(settings)
    settings = settings["evaluation"]
    unseen = set(pd.concat([validation["cc_num"], test["cc_num"]])) - set(
        train["cc_num"]
    )
    preprocessor = ColumnTransformer(
        [
            ("amount", StandardScaler(), ["log_amount"]),
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore", dtype=np.float32),
                ["hour", "category"],
            ),
        ]
    )
    # 스케일과 범주 목록을 학습 기간에서만 결정한다.
    train_inputs = preprocessor.fit_transform(inputs(train))
    validation_inputs = preprocessor.transform(inputs(validation))
    test_inputs = preprocessor.transform(inputs(test))
    seed = runs["seed"]
    workers = runs["workers"]
    models = {
        "amount_rule": None,
        "logistic_regression": LogisticRegression(
            random_state=seed, **runs["logistic_regression"]
        ),
        "random_forest": RandomForestClassifier(
            random_state=seed, n_jobs=workers, **runs["random_forest"]
        ),
        "xgboost": XGBClassifier(random_state=seed, n_jobs=workers, **runs["xgboost"]),
    }
    output = ROOT / "artifacts/baseline"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, output / "preprocessor.joblib")
    results = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **{
                name: version(name)
                for name in ("numpy", "pandas", "scikit-learn", "xgboost")
            },
        },
        "models": {},
    }
    for name, model in models.items():
        print(f"Running {name}", flush=True)
        start = perf_counter()
        if model is not None:
            with threadpool_limits(limits=workers):
                model.fit(train_inputs, train["is_fraud"].to_numpy())
        fit_seconds = perf_counter() - start if model is not None else None
        if isinstance(model, RandomForestClassifier):
            # 트리 점수의 합산 순서를 고정해 기준점 근처 거래가 실행마다 바뀌지 않게 한다.
            model.set_params(n_jobs=1)
        scores = (
            validation["amt"].to_numpy()
            if model is None
            else model.predict_proba(validation_inputs)[:, 1]
        )
        threshold = choose_threshold(
            validation["is_fraud"].to_numpy(),
            scores,
            settings["review_cost_units"],
            settings["primary_missed_fraud_cost_units"],
        )
        start = perf_counter()
        test_scores = (
            test["amt"].to_numpy()
            if model is None
            else model.predict_proba(test_inputs)[:, 1]
        )
        predict_seconds = perf_counter() - start
        results["models"][name] = {
            "threshold_from_validation": threshold,
            "fit_seconds": fit_seconds,
            "test_scoring_seconds": predict_seconds,
            "validation": evaluate(validation, scores, threshold, settings, unseen),
            "test": evaluate(test, test_scores, threshold, settings, unseen),
        }
        if model is not None:
            joblib.dump(model, output / f"{name}.joblib")
    (output / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(output / "results.json")


if __name__ == "__main__":
    main()
