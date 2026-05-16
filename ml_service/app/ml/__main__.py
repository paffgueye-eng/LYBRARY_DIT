"""Entraînement CLI : python -m app.ml.train"""
import logging

from app.core.logging_config import setup_logging
from app.database import SessionLocal
from app.ml.train import run_training

if __name__ == "__main__":
    setup_logging()
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        stats = run_training(db)
        print("Training complete:", stats)
