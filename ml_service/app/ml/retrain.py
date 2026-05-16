"""
Ré-entraînement : récupère les nouvelles données et remplace les artefacts.
"""
import logging

from sqlalchemy.orm import Session

from app.ml.services import train_model

logger = logging.getLogger(__name__)


def retrain_model(
    db: Session,
    *,
    min_df: int = 1,
    max_features: int = 5000,
) -> dict:
    logger.info("Démarrage du ré-entraînement…")
    stats = train_model(db, min_df=min_df, max_features=max_features)
    logger.info("Ré-entraînement terminé : %s", stats)
    return stats
