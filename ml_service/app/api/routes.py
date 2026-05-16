import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.cache import recommendation_cache
from app.core.exceptions import (
    ModelNotReadyError,
    UserNotFoundError,
    http_model_not_ready,
    http_user_not_found,
)
from app.core.security import optional_auth
from app.database import get_db
from app.ml.predict import predict_for_user
from app.ml.retrain import retrain_model
from app.ml.services import is_model_loaded, load_model
from app.schemas import (
    HealthResponse,
    RecommendationResponse,
    SimilarBooksResponse,
    TrainRequest,
    TrainResponse,
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(db: Session = Depends(get_db)):
    from sqlalchemy import text

    db_ok = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        db_ok = "error"

    loaded = False
    try:
        load_model()
        loaded = True
    except ModelNotReadyError:
        loaded = False

    return HealthResponse(
        status="ok" if db_ok == "ok" else "degraded",
        model_loaded=loaded,
        database=db_ok,
    )


@router.get(
    "/recommendations/{user_id}",
    response_model=RecommendationResponse,
    tags=["recommendations"],
)
@limiter.limit("60/minute")
async def get_recommendations(
    request: Request,
    user_id: int,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    db: Session = Depends(get_db),
    _auth=Depends(optional_auth),
    settings: Settings = Depends(get_settings),
):
    cache_key = (user_id, limit)
    if cache_key in recommendation_cache:
        cached = recommendation_cache[cache_key]
        return RecommendationResponse(**cached)

    try:
        items, version = predict_for_user(db, user_id, limit=limit or settings.default_top_n)
    except ModelNotReadyError:
        raise http_model_not_ready() from None
    except UserNotFoundError:
        raise http_user_not_found(user_id) from None

    payload = {
        "user_id": user_id,
        "recommendations": items,
        "model_version": version,
    }
    recommendation_cache[cache_key] = payload
    return RecommendationResponse(**payload)


@router.get(
    "/recommendations/similar/{book_id}",
    response_model=SimilarBooksResponse,
    tags=["recommendations"],
)
@limiter.limit("60/minute")
async def get_similar_books(
    request: Request,
    book_id: int,
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
    db: Session = Depends(get_db),
    _auth=Depends(optional_auth),
):
    from app.ml.services import recommend_similar_books

    try:
        load_model()
        items = recommend_similar_books(db, book_id, limit=limit)
    except ModelNotReadyError:
        raise http_model_not_ready() from None

    return SimilarBooksResponse(book_id=book_id, recommendations=items)


@router.post("/train", response_model=TrainResponse, tags=["training"])
@limiter.limit("10/hour")
async def train_endpoint(
    request: Request,
    body: TrainRequest | None = None,
    db: Session = Depends(get_db),
    _auth=Depends(optional_auth),
):
    params = body or TrainRequest()
    try:
        stats = retrain_model(
            db,
            min_df=params.min_df,
            max_features=params.max_features,
        )
        recommendation_cache.clear()
        return TrainResponse(
            status="success",
            message="Model retrained successfully",
            books_count=stats.get("books_count", 0),
            loans_count=stats.get("loans_count", 0),
        )
    except ValueError as exc:
        logger.exception("Training failed")
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Training failed")
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Training failed") from exc
