#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Évaluer un modèle de recommandation et sauvegarder les métriques.")
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "models" / "model.pkl",
        help="Chemin du modèle entraîné.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "loans_clean.csv",
        help="Chemin du CSV prétraité.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metrics" / "metrics.json",
        help="Chemin du fichier de métriques JSON.",
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


def load_model(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"Modèle introuvable : {model_path}")
    return joblib.load(model_path)


def load_dataset(data_path: Path) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    if df.empty:
        raise ValueError("Le fichier de données est vide. Exécutez d'abord preprocess.py.")
    required = ["user_id", "book_id", "rating"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour l'évaluation : {missing}")
    return df


def build_test_set(df: pd.DataFrame, test_size: float, random_state: int) -> pd.DataFrame:
    _, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        shuffle=True,
    )
    return test_df


def predict_rating(model: object, user_id: int, book_id: int) -> float:
    try:
        prediction = model.predict(user_id, book_id)
    except Exception:
        return float(model.trainset.global_mean)
    return float(prediction.est)


def save_metrics(metrics: dict[str, float], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as outfile:
        json.dump(metrics, outfile, indent=2, ensure_ascii=False)


def main() -> None:
    args = parse_args()
    params = load_params(args.params)
    eval_params = params.get("evaluate", {})

    model = load_model(args.model)
    df = load_dataset(args.data)
    test_df = build_test_set(
        df,
        float(eval_params.get("test_size", 0.2)),
        int(eval_params.get("random_state", 42)),
    )

    y_true = test_df["rating"].astype(float).to_numpy()
    y_pred = np.array([
        predict_rating(model, int(row["user_id"]), int(row["book_id"]))
        for _, row in test_df.iterrows()
    ])

    metrics = {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "n_predictions": int(len(y_true)),
    }
    save_metrics(metrics, args.output)
    print(f"Métriques sauvegardées : {args.output}")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
