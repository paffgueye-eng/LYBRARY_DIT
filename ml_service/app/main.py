import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import limiter, router
from app.config import get_settings
from app.core.exceptions import ModelNotReadyError
from app.core.logging_config import setup_logging
from app.ml.services import is_model_loaded, load_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    if is_model_loaded():
        try:
            load_model()
            logger.info("Artefacts ML pré-chargés au démarrage.")
        except ModelNotReadyError:
            logger.warning(
                "Aucun modèle trouvé — lancez POST /train ou python -m app.ml.train"
            )
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DIT Library — Recommendation AI",
        description=(
            "Microservice de recommandation de livres (TF-IDF + similarité cosinus) "
            "pour la bibliothèque numérique DIT."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ModelNotReadyError)
    async def model_not_ready_handler(_request: Request, _exc: ModelNotReadyError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Modèle non entraîné. Exécutez POST /train."},
        )

    app.include_router(router)
    return app


app = create_app()
