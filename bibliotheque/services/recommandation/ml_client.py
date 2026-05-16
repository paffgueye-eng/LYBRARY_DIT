"""
Client HTTP vers le microservice FastAPI de recommandation.
"""
import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return getattr(settings, "RECOMMENDATION_SERVICE_URL", "http://localhost:8001").rstrip("/")


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = getattr(settings, "RECOMMENDATION_API_KEY", "") or ""
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def fetch_recommendations(user_id: int, limit: int = 12) -> list[dict[str, Any]] | None:
    """
    Appelle GET /recommendations/{user_id}.
    Retourne None si le service est indisponible (fallback Django).
    """
    url = f"{_base_url()}/recommendations/{user_id}"
    timeout = getattr(settings, "RECOMMENDATION_SERVICE_TIMEOUT", 8)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params={"limit": limit}, headers=_headers())
            response.raise_for_status()
            return response.json().get("recommendations", [])
    except httpx.HTTPError as exc:
        logger.warning("ML service unavailable for user %s: %s", user_id, exc)
        return None


def trigger_retrain() -> dict[str, Any] | None:
    """POST /train — réentraînement (admin / tâche planifiée)."""
    url = f"{_base_url()}/train"
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(url, json={}, headers=_headers())
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        logger.error("ML retrain failed: %s", exc)
        return None
