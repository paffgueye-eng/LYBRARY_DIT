#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import LabelEncoder

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_STATUS_RATINGS = {
    "returned": 5,
    "renewed": 4,
    "active": 3,
    "overdue": 2,
    "unknown": 3,
}


def load_raw_csv(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        input_path,
        parse_dates=["borrowed_at", "due_date", "returned_at", "created_at"],
        low_memory=False,
    )
    return df


def validate_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans le CSV d'entrée : {', '.join(missing)}")


def normalize_dataframe(df: pd.DataFrame, status_map: dict[str, int]) -> pd.DataFrame:
    df = df.copy()
    df["status"] = df["status"].fillna("unknown").astype(str).str.lower()
    df["rating"] = df["status"].map(status_map).fillna(status_map["unknown"]).astype(int)
    df["category_name"] = df.get("category_name", "unknown").fillna("unknown").astype(str)
    df["book_author"] = df.get("book_author", "unknown").fillna("unknown").astype(str)
    df["book_title"] = df.get("book_title", "unknown").fillna("unknown").astype(str)

    for date_column in ["borrowed_at", "due_date", "returned_at", "created_at"]:
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

    df = df.dropna(subset=["user_id", "book_id", "borrowed_at"])
    df = df.drop_duplicates(subset=["user_id", "book_id", "borrowed_at", "status"])

    encoder = LabelEncoder()
    df["category_label"] = encoder.fit_transform(df["category_name"])
    df["author_label"] = encoder.fit_transform(df["book_author"])

    return df


def save_processed(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nettoyer et encoder les données de prêt pour DVC.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "loans.csv",
        help="Chemin du CSV brut à prétraiter.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "loans_clean.csv",
        help="Chemin de sortie du CSV prétraité.",
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=PROJECT_ROOT / "params.yaml",
        help="Chemin du fichier params.yaml.",
    )
    return parser.parse_args()


def load_params(params_path: Path) -> dict[str, object]:
    import yaml

    with params_path.open("r", encoding="utf-8") as infile:
        return yaml.safe_load(infile) or {}


def main() -> None:
    args = parse_args()
    params = load_params(args.params)
    preprocess_params = params.get("preprocess", {})
    status_rating_map = {
        **DEFAULT_STATUS_RATINGS,
        **preprocess_params.get("status_rating_map", {}),
    }

    df = load_raw_csv(args.input)
    validate_columns(df, preprocess_params.get("required_columns", []))
    cleaned_df = normalize_dataframe(df, status_rating_map)
    save_processed(cleaned_df, args.output)
    print(f"CSV prétraité sauvegardé : {args.output} ({len(cleaned_df)} lignes)")


if __name__ == "__main__":
    main()
