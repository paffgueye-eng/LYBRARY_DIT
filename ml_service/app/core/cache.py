from cachetools import TTLCache

from app.config import get_settings

_settings = get_settings()

# Cache des réponses de recommandation par (user_id, limit)
recommendation_cache: TTLCache = TTLCache(
    maxsize=512,
    ttl=_settings.recommendation_cache_ttl,
)
