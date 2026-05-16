"""
Services ML : chargement unique du modèle, recommandations, entraînement.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.core.exceptions import ModelNotReadyError, UserNotFoundError
from app.ml.train import run_training
from app.models_db import Book, Loan, User

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()


@dataclass
class ModelArtifacts:
    vectorizer: Any
    dataframe: pd.DataFrame
    model: dict
    version: str


_artifacts: ModelArtifacts | None = None


def _artifacts_exist(settings: Settings) -> bool:
    return (
        settings.vectorizer_path.is_file()
        and settings.dataframe_path.is_file()
        and settings.model_path.is_file()
    )


def load_model(*, force: bool = False) -> ModelArtifacts:
    """Charge vectorizer, dataframe et modèle une seule fois (thread-safe)."""
    global _artifacts
    settings = get_settings()

    if _artifacts is not None and not force:
        return _artifacts

    with _load_lock:
        if _artifacts is not None and not force:
            return _artifacts

        if not _artifacts_exist(settings):
            raise ModelNotReadyError("Fichiers modèle introuvables.")

        vectorizer = joblib.load(settings.vectorizer_path)
        dataframe = joblib.load(settings.dataframe_path)
        model = joblib.load(settings.model_path)
        version = model.get("version", "unknown")

        _artifacts = ModelArtifacts(
            vectorizer=vectorizer,
            dataframe=dataframe,
            model=model,
            version=version,
        )
        logger.info("Modèle IA chargé (version %s)", version)
        return _artifacts


def unload_model() -> None:
    global _artifacts
    with _load_lock:
        _artifacts = None


def is_model_loaded() -> bool:
    return _artifacts is not None or _artifacts_exist(get_settings())


def _cover_url(cover: str | None, settings: Settings) -> str | None:
    if not cover:
        return None
    base = settings.media_base_url.rstrip("/")
    path = cover if cover.startswith("/") else f"/{cover}"
    if not path.startswith("/media/"):
        path = f"/media/{cover.lstrip('/')}"
    return f"{base}{path}"


def _user_borrowed_book_ids(db: Session, user_id: int) -> set[int]:
    rows = db.scalars(
        select(Loan.book_id).where(Loan.user_id == user_id)
    ).all()
    return set(rows)


def _user_category_weights(db: Session, user_id: int) -> dict[int, float]:
    """Poids par catégorie selon l'historique d'emprunts."""
    stmt = (
        select(Loan)
        .where(Loan.user_id == user_id)
        .options(joinedload(Loan.book).joinedload(Book.category))
    )
    loans = db.scalars(stmt).unique().all()
    weights: dict[int, float] = {}
    for loan in loans:
        book = loan.book
        if not book or not book.category_id:
            continue
        w = 2.0 if loan.status == "returned" else 1.5
        weights[book.category_id] = weights.get(book.category_id, 0.0) + w
    return weights


def _loan_popularity(db: Session) -> dict[int, int]:
    counts: dict[int, int] = {}
    for book_id in db.scalars(select(Loan.book_id)).all():
        counts[book_id] = counts.get(book_id, 0) + 1
    return counts


def recommend_books(
    db: Session,
    user_id: int,
    *,
    limit: int = 12,
) -> tuple[list[dict], str]:
    """
    Recommandations hybrides :
    - profil TF-IDF moyen des livres empruntés + similarité cosinus
    - similarité inter-livres (item-item)
    - boost catégories préférées
    - exclusion des livres déjà empruntés
    - cold start : popularité + contenu
    """
    settings = get_settings()
    artifacts = load_model()

    if db.get(User, user_id) is None:
        raise UserNotFoundError(user_id)

    df = artifacts.dataframe
    model = artifacts.model
    similarity_matrix: np.ndarray = model["similarity_matrix"]
    tfidf_matrix = model["tfidf_matrix"]
    book_id_to_idx: dict[int, int] = model["book_id_to_idx"]

    borrowed_ids = _user_borrowed_book_ids(db, user_id)
    category_weights = _user_category_weights(db, user_id)
    loan_counts = _loan_popularity(db)
    max_loans = max(loan_counts.values(), default=1)

    scores: dict[int, float] = {}
    borrowed_indices = [
        book_id_to_idx[bid] for bid in borrowed_ids if bid in book_id_to_idx
    ]

    if borrowed_indices:
        profile = np.asarray(tfidf_matrix[borrowed_indices].mean(axis=0))
        profile_scores = cosine_similarity(profile, tfidf_matrix).flatten()
        for idx, score in enumerate(profile_scores):
            book_id = int(df.iloc[idx]["id"])
            if book_id not in borrowed_ids:
                scores[book_id] = float(score)

        for b_idx in borrowed_indices[:5]:
            for idx, sim in enumerate(similarity_matrix[b_idx]):
                book_id = int(df.iloc[idx]["id"])
                if book_id not in borrowed_ids:
                    scores[book_id] = max(scores.get(book_id, 0.0), float(sim) * 0.9)
    else:
        mean_content = similarity_matrix.mean(axis=0)
        for idx, content_score in enumerate(mean_content):
            book_id = int(df.iloc[idx]["id"])
            if book_id in borrowed_ids:
                continue
            pop = loan_counts.get(book_id, 0) / max_loans
            scores[book_id] = 0.35 * float(content_score) + 0.65 * pop

    for book_id in scores:
        row = df[df["id"] == book_id]
        if row.empty:
            continue
        cat_id = row.iloc[0].get("category_id")
        if cat_id and cat_id in category_weights:
            scores[book_id] += min(category_weights[cat_id] * 0.05, 0.2)
        if int(row.iloc[0].get("available_copies") or 0) > 0:
            scores[book_id] += 0.02

    if not scores:
        return [], artifacts.version

    max_score = max(scores.values())
    min_score = min(scores.values())
    span = max_score - min_score or 1.0

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    recommendations = []
    for book_id, raw in ranked:
        row = df[df["id"] == book_id].iloc[0]
        normalized = round(min(max((raw - min_score) / span, 0.05), 1.0), 2)
        recommendations.append(
            {
                "id": int(book_id),
                "title": str(row["title"]),
                "author": str(row["author"]),
                "category": str(row["category_name"]) or None,
                "score": normalized,
                "cover_url": _cover_url(row.get("cover"), settings),
            }
        )

    return recommendations, artifacts.version


def recommend_similar_books(
    db: Session,
    book_id: int,
    *,
    limit: int = 6,
) -> list[dict]:
    """Livres similaires par matrice de similarité cosinus (TF-IDF)."""
    settings = get_settings()
    artifacts = load_model()
    df = artifacts.dataframe
    model = artifacts.model
    similarity_matrix: np.ndarray = model["similarity_matrix"]
    book_id_to_idx: dict[int, int] = model["book_id_to_idx"]

    if book_id not in book_id_to_idx:
        return []

    idx = book_id_to_idx[book_id]
    sims = similarity_matrix[idx]
    ranked_idx = np.argsort(sims)[::-1]

    results = []
    for other_idx in ranked_idx:
        if other_idx == idx:
            continue
        other_id = int(df.iloc[other_idx]["id"])
        row = df.iloc[other_idx]
        results.append(
            {
                "id": other_id,
                "title": str(row["title"]),
                "author": str(row["author"]),
                "category": str(row["category_name"]) or None,
                "score": round(float(sims[other_idx]), 2),
                "cover_url": _cover_url(row.get("cover"), settings),
            }
        )
        if len(results) >= limit:
            break
    return results


def train_model(
    db: Session,
    *,
    min_df: int = 1,
    max_features: int = 5000,
) -> dict:
    stats = run_training(db, min_df=min_df, max_features=max_features)
    unload_model()
    load_model(force=True)
    return stats
