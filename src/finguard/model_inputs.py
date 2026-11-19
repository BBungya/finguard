"""학습과 API에서 같은 순서의 모델 입력을 만든다."""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def inputs(rows):
    # 카드 번호와 정답 라벨은 모델 입력에 포함하지 않는다.
    return pd.DataFrame(
        {
            "log_amount": np.log1p(rows["amt"]).astype(np.float32),
            "hour": rows["trans_date_trans_time"].dt.hour,
            "category": rows["category"],
        }
    )


def make_preprocessor(categorical_columns=("hour", "category")):
    return ColumnTransformer(
        [
            ("amount", StandardScaler(), ["log_amount"]),
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore", dtype=np.float32),
                list(categorical_columns),
            ),
        ]
    )


def add_history(base, history):
    # XGBoost에서 0이 결측으로 해석되지 않도록 추가 열의 0도 명시한다.
    rows, columns = history.shape
    explicit_history = csr_matrix(
        (
            history.ravel(),
            np.tile(np.arange(columns), rows),
            np.arange(0, (rows + 1) * columns, columns),
        ),
        shape=history.shape,
    )
    return hstack((base, explicit_history), format="csr")


def behavior_values(history, scaler, cluster, anomaly, *, include_anomaly=True):
    known = history[:, 1] > 0
    groups = np.full(len(history), -1, dtype=int)
    scores = np.full((len(history), 1), -1.0, dtype=np.float32)
    if known.any():
        transformed = scaler.transform(np.log1p(history[known])).astype(
            cluster.cluster_centers_.dtype, copy=False
        )
        groups[known] = cluster.predict(transformed)
        if include_anomaly:
            scores[known, 0] = -anomaly.score_samples(transformed)
    # 그룹마다 별도 열을 만들어 번호 크기가 위험 순서로 쓰이지 않게 한다.
    membership = np.eye(cluster.n_clusters + 1, dtype=np.float32)[groups + 1]
    return groups, membership, scores


def variant_inputs(base, membership, scores, name):
    if name == "cluster":
        return add_history(base, membership)
    if name == "anomaly":
        return add_history(base, scores)
    if name == "both":
        return add_history(base, np.column_stack((membership, scores)))
    return base
