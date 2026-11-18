"""Handbook에서 같은 XGBoost 설정으로 카드 이력 추가 전후를 비교한다."""

import hashlib
import json
from itertools import pairwise

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from train_baselines import ROOT, inputs, make_preprocessor
from tune_history_models import add_history, history_inputs, read_settings
from xgboost import XGBClassifier

from finguard.baseline_metrics import choose_threshold, evaluate
from finguard.features import FEATURE_VERSION

HANDBOOK_COLUMNS = {
    "TRANSACTION_ID": "trans_num",
    "TX_DATETIME": "trans_date_trans_time",
    "CUSTOMER_ID": "cc_num",
    "TX_AMOUNT": "amt",
    "TX_FRAUD": "is_fraud",
}


def load_handbook(settings):
    manifest = json.loads(
        (ROOT / settings["dataset_manifest"]).read_text(encoding="utf-8")
    )
    path = ROOT / manifest["local_directory"] / manifest["file"]
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if checksum != manifest["csv_sha256"]:
        raise ValueError("Handbook CSV의 SHA-256이 매니페스트와 다릅니다.")

    rows = pd.read_csv(
        path,
        usecols=list(HANDBOOK_COLUMNS),
        dtype={"TRANSACTION_ID": str, "CUSTOMER_ID": str, "TX_AMOUNT": float},
    ).rename(columns=HANDBOOK_COLUMNS)
    rows["trans_date_trans_time"] = pd.to_datetime(
        rows["trans_date_trans_time"], format="%Y-%m-%d %H:%M:%S"
    )
    if (
        rows.isna().any().any()
        or rows["trans_num"].duplicated().any()
        or not rows["is_fraud"].isin([0, 1]).all()
        or not (np.isfinite(rows["amt"]) & (rows["amt"] >= 0)).all()
    ):
        raise ValueError("Handbook 거래 값이나 라벨이 유효하지 않습니다.")
    # FinGuard의 금액 검증은 양수 거래를 요구한다.
    zero = rows["amt"] == 0
    excluded = {"rows": int(zero.sum()), "fraud": int(rows.loc[zero, "is_fraud"].sum())}
    rows = rows.loc[~zero].copy()
    # 업종은 제공되지 않는다. 공통 이력 계산기의 거래 입력 형태만 채운다.
    rows["category"] = "unknown"

    dates = rows["trans_date_trans_time"]
    boundaries = [
        settings["periods"][key]
        for key in ("train_start", "validation_start", "test_start", "end_exclusive")
    ]
    if any(start >= stop for start, stop in pairwise(boundaries)):
        raise ValueError("분할 경계는 시간순이어야 합니다.")
    periods = tuple(
        rows.loc[(dates >= start) & (dates < stop)]
        for start, stop in pairwise(boundaries)
    )
    if sum(map(len, periods)) != len(rows) or any(
        part["is_fraud"].nunique() != 2 for part in periods
    ):
        raise ValueError(
            "거래가 분할에서 누락되거나 정상·사기 라벨이 없는 기간이 있습니다."
        )
    return periods, excluded


def main():
    config = read_settings("handbook_benchmark.toml")
    baseline = read_settings("baseline.toml")
    evaluation = read_settings("ml_split.toml")["evaluation"]
    periods, excluded = load_handbook(config)
    train, validation, test = periods
    preprocessor = make_preprocessor(("hour",))
    base_train = preprocessor.fit_transform(inputs(train))
    base_validation = preprocessor.transform(inputs(validation))
    base_test = preprocessor.transform(inputs(test))
    base_inputs = (base_train, base_validation, base_test)
    history = history_inputs(periods)
    unseen = set(pd.concat([validation["cc_num"], test["cc_num"]])) - set(
        train["cc_num"]
    )
    labels = train["is_fraud"].to_numpy()
    validation_labels = validation["is_fraud"].to_numpy()
    workers = baseline["workers"]
    model_settings = baseline["xgboost"] | config["xgboost"]
    results = {
        "history_feature_version": FEATURE_VERSION,
        "xgboost_settings": model_settings,
        "zero_amount_excluded": excluded,
        "periods": {
            name: {"rows": len(frame), "fraud": int(frame["is_fraud"].sum())}
            for name, frame in zip(
                ("train", "validation", "test"), periods, strict=True
            )
        },
        "models": {},
    }

    for name in ("base", "history"):
        print(f"Comparing Handbook XGBoost: {name}", flush=True)
        train_inputs, validation_inputs, test_inputs = base_inputs
        if name == "history":
            train_inputs = add_history(base_train, next(history))
            validation_inputs = add_history(base_validation, next(history))
        model = XGBClassifier(
            random_state=baseline["seed"], n_jobs=workers, **model_settings
        )
        with threadpool_limits(limits=workers):
            model.fit(train_inputs, labels)
        validation_scores = model.predict_proba(validation_inputs)[:, 1]
        threshold = choose_threshold(
            validation_labels,
            validation_scores,
            evaluation["review_cost_units"],
            evaluation["primary_missed_fraud_cost_units"],
        )
        if name == "history":
            test_inputs = add_history(base_test, next(history))
        test_scores = model.predict_proba(test_inputs)[:, 1]
        results["models"][name] = {
            "threshold_from_validation": threshold,
            "validation": evaluate(
                validation, validation_scores, threshold, evaluation, unseen
            ),
            "test": evaluate(test, test_scores, threshold, evaluation, unseen),
        }

    output = ROOT / "artifacts/handbook_benchmark/results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
