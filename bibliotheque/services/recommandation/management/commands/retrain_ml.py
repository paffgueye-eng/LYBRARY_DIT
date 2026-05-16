"""
Réentraîne le microservice IA : POST /train

Usage:
    python manage.py retrain_ml
"""
from django.core.management.base import BaseCommand

from services.recommandation.ml_client import trigger_retrain


class Command(BaseCommand):
    help = "Déclenche le ré-entraînement du modèle de recommandation (microservice FastAPI)."

    def handle(self, *args, **options):
        result = trigger_retrain()
        if result:
            self.stdout.write(self.style.SUCCESS(result.get("message", "OK")))
        else:
            self.stderr.write(
                "Échec — vérifiez que le service tourne sur RECOMMENDATION_SERVICE_URL."
            )
