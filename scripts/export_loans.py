#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_database_url(explicit: str | None) -> str:
    if explicit:
        return explicit

    dotenv_path = PROJECT_ROOT / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    env_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not env_url:
        raise ValueError(
            "DATABASE_URL n'est pas défini. Ajoute DATABASE_URL dans .env ou utilise --database-url."
        )
    return env_url


def export_loans(output_path: Path, database_url: str) -> int:
    engine = create_engine(database_url, future=True)
    query = text(
        """
        SELECT
            l.id AS loan_id,
            l.user_id,
            l.book_id,
            b.title AS book_title,
            b.author AS book_author,
            c.id AS category_id,
            c.name AS category_name,
            l.borrowed_at,
            l.due_date,
            l.returned_at,
            l.status,
            l.created_at
        FROM loans_loan l
        LEFT JOIN books_book b ON b.id = l.book_id
        LEFT JOIN books_category c ON c.id = b.category_id
        ORDER BY l.borrowed_at ASC
        """
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            df = pd.DataFrame(result.mappings().all())
    except SQLAlchemyError as error:
        raise RuntimeError(f"Impossible de se connecter à PostgreSQL : {error}") from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    return len(df)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporter l'historique des emprunts PostgreSQL vers CSV.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "loans.csv",
        help="Chemin de sortie du CSV exporté.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="URL de connexion PostgreSQL. Si absent, DATABASE_URL est lu depuis .env.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_url = load_database_url(args.database_url)
    record_count = export_loans(args.output, database_url)
    print(f"CSV exporté : {args.output} ({record_count} lignes)")


if __name__ == "__main__":
    main()
