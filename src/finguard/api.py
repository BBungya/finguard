"""거래 한 건을 검증하고 위험 점수를 반환하는 로컬 API."""

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Self

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from finguard.features import HistoryFeatures
from finguard.scoring import (
    InMemoryScoringService,
    ScoringModel,
    ScoringUnavailable,
    TransactionConflict,
)
from finguard.transactions import Transaction


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transaction_id: str = Field(min_length=1)
    card_id: str = Field(min_length=1)
    occurred_at: str
    amount: str
    category: str = Field(min_length=1)

    def transaction(self) -> Transaction:
        return Transaction.from_csv_row(
            {
                "trans_num": self.transaction_id,
                "cc_num": self.card_id,
                "trans_date_trans_time": self.occurred_at,
                "amt": self.amount,
                "category": self.category,
            }
        )

    @model_validator(mode="after")
    def validate_transaction(self) -> Self:
        self.transaction()
        return self


class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float = Field(ge=0, le=1)
    review_required: bool
    threshold: float | None
    cluster_id: int
    model_version: str
    policy_version: str
    features: HistoryFeatures


def create_app(model=None, *, database_url=None, redis_url=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        # 서버 시작 때 한 번 읽어 요청마다 같은 모델을 사용한다.
        loaded = model
        if loaded is None:
            path = Path(
                os.environ.get(
                    "SCORING_MODEL_PATH",
                    "artifacts/behavior_ablation/selected_model.joblib",
                )
            )
            loaded = ScoringModel(path)
        url = (
            os.environ.get("DATABASE_URL", "") if database_url is None else database_url
        ).strip()
        cache_url = (
            os.environ.get("REDIS_URL", "") if redis_url is None else redis_url
        ).strip()
        if cache_url and not url:
            raise ValueError("REDIS_URL을 사용하려면 DATABASE_URL도 설정하세요.")
        cache = None
        if cache_url:
            from finguard.history_cache import RedisHistoryCache

            cache = RedisHistoryCache(cache_url, url)
        if url:
            from finguard.database import PostgresScoringService

            app.state.scoring = PostgresScoringService(loaded, url, history_cache=cache)
        else:
            app.state.scoring = InMemoryScoringService(loaded)
        try:
            yield
        finally:
            if cache is not None:
                cache.close()

    application = FastAPI(
        title="FinGuard 거래 점수 API", version="0.1.0", lifespan=lifespan
    )

    @application.post("/transactions/score", response_model=ScoreResponse)
    def score_transaction(payload: ScoreRequest):
        try:
            result = application.state.scoring.score(payload.transaction())
        except TransactionConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ScoringUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return asdict(result)

    return application


app = create_app()
