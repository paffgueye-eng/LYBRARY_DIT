"""
Couche prédiction — délègue à services.recommend_books.
"""
from sqlalchemy.orm import Session

from app.ml.services import recommend_books as _recommend_books


def predict_for_user(db: Session, user_id: int, limit: int = 12) -> tuple[list[dict], str]:
    return _recommend_books(db, user_id, limit=limit)
