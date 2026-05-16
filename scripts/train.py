#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from surprise import Dataset, Reader, SVD, KNNBasic, accuracy
from surprise.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entraîner un modèle de recommandation avec scikit-surprise.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "loans_clean.csv",
        help="Chemin du CSV prétraité.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "models" / "model.pkl",
        help="Chemin du modèle sauvegardé.",
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


def load_dataset(input_path: Path) -> tuple[Dataset, pd.DataFrame]:
    df = pd.read_csv(input_path)
    if df.empty:
        raise ValueError("Le fichier de données est vide. Exécutez d'abord preprocess.py.")
    required = ["user_id", "book_id", "rating"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour l'entraînement : {missing}")

    reader = Reader(rating_scale=(1, 5))
    dataset = Dataset.load_from_df(df[["user_id", "book_id", "rating"]], reader)
    return dataset, df


def build_algorithm(config: dict[str, object]):
    algorithm = config.get("algorithm", "svd")
    if algorithm == "svd":
        return SVD(
            n_factors=int(config.get("n_factors", 50)),
            n_epochs=int(config.get("n_epochs", 20)),
            lr_all=float(config.get("lr_all", 0.005)),
            reg_all=float(config.get("reg_all", 0.02)),
        )
    if algorithm == "knn":
        return KNNBasic(
            k=int(config.get("k", 20)),
            min_k=int(config.get("min_k", 1)),
        )
    raise ValueError(f"Algorithme inconnu : {algorithm}")


def train_model(dataset: Dataset, algo_config: dict[str, object]) -> tuple[object, dict[str, float]]:
    trainset, _ = train_test_split(dataset, test_size=0.2, random_state=int(algo_config.get("random_state", 42)))
    algorithm = build_algorithm(algo_config)
    algorithm.fit(trainset)

    predictions = algorithm.test(trainset.build_testset())
    metrics = {
        "train_rmse": accuracy.rmse(predictions, verbose=False),
        "train_mae": accuracy.mae(predictions, verbose=False),
    }
    return algorithm, metrics


def save_model(model: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)


def main() -> None:
    args = parse_args()
    params = load_params(args.params)
    train_params = params.get("train", {})

    dataset, _ = load_dataset(args.input)
    model, metrics = train_model(dataset, train_params)
    save_model(model, args.output)

    print(f"Modèle entraîné sauvegardé : {args.output}")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
