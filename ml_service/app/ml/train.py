"""
Entraînement du moteur de recommandation :
- chargement PostgreSQL
- preprocessing texte (titre, auteur, description, catégorie, mots-clés)
- TF-IDF + matrice de similarité cosinus
- sauvegarde joblib (vectorizer.pkl, dataframe.pkl, model.pkl)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.models_db import Book, Category, Loan

logger = logging.getLogger(__name__)


def _book_corpus(row: pd.Series) -> str:
    parts = [
        str(row.get("title") or ""),
        str(row.get("author") or ""),
        str(row.get("category_name") or ""),
        str(row.get("description") or ""),
        str(row.get("keywords") or ""),
    ]
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def fetch_training_dataframe(db: Session) -> tuple[pd.DataFrame, int]:
    """Construit le DataFrame livres + compte les emprunts."""
    stmt = (
        select(Book)
        .options(joinedload(Book.category))
        .order_by(Book.id)
    )
    books = db.scalars(stmt).unique().all()

    rows = []
    for book in books:
        cat: Category | None = book.category
        cover_path = book.cover or ""
        rows.append(
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "description": book.description or "",
                "keywords": book.keywords or "",
                "category_id": book.category_id,
                "category_name": cat.name if cat else "",
                "category_slug": cat.slug if cat else "",
                "year": book.year,
                "available_copies": book.available_copies,
                "cover": cover_path,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df, 0

    df["corpus"] = df.apply(_book_corpus, axis=1)
    df["corpus"] = df["corpus"].str.replace(r"\s+", " ", regex=True).str.strip()

    from sqlalchemy import func

    total_loans = db.scalar(select(func.count()).select_from(Loan)) or 0
    return df, int(total_loans)


def train_from_dataframe(
    df: pd.DataFrame,
    *,
    min_df: int = 1,
    max_features: int = 5000,
    settings: Settings | None = None,
) -> dict:
    settings = settings or get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    if df.empty or len(df) < 2:
        raise ValueError("Pas assez de livres pour entraîner le modèle (minimum 2).")

    vectorizer = TfidfVectorizer(
        min_df=min_df,
        max_features=max_features,
        stop_words=None,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(df["corpus"])
    similarity_matrix = cosine_similarity(tfidf_matrix)

    book_id_to_idx = {int(bid): idx for idx, bid in enumerate(df["id"].tolist())}
    idx_to_book_id = {idx: int(bid) for bid, idx in book_id_to_idx.items()}

    model_bundle = {
        "similarity_matrix": similarity_matrix,
        "tfidf_matrix": tfidf_matrix,
        "book_id_to_idx": book_id_to_idx,
        "idx_to_book_id": idx_to_book_id,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    }

    joblib.dump(vectorizer, settings.vectorizer_path)
    joblib.dump(df, settings.dataframe_path)
    joblib.dump(model_bundle, settings.model_path)

    logger.info(
        "Modèle sauvegardé : %d livres, matrice %s",
        len(df),
        similarity_matrix.shape,
    )
    return {
        "books_count": len(df),
        "matrix_shape": similarity_matrix.shape,
        "version": model_bundle["version"],
    }


def run_training(
    db: Session,
    *,
    min_df: int = 1,
    max_features: int = 5000,
) -> dict:
    df, loans_count = fetch_training_dataframe(db)
    stats = train_from_dataframe(df, min_df=min_df, max_features=max_features)
    stats["loans_count"] = loans_count
    return stats
