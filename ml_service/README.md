# DIT Library — Microservice IA (Recommandations)

API FastAPI de recommandation de livres basée sur **TF-IDF** et **similarité cosinus**, entraînée sur l'historique d'emprunts PostgreSQL (base Django).

## Stack

- FastAPI, Uvicorn
- Scikit-learn, Pandas, Joblib
- SQLAlchemy + PostgreSQL
- SlowAPI (rate limiting), JWT / API Key optionnels

## Structure

```
ml_service/
├── app/
│   ├── main.py           # Point d'entrée FastAPI
│   ├── config.py         # Settings (pydantic-settings)
│   ├── database.py       # Session SQLAlchemy
│   ├── models_db.py      # Tables Django (users, books, loans)
│   ├── schemas.py        # Modèles Pydantic
│   ├── api/routes.py     # Endpoints REST
│   ├── core/             # Cache, sécurité, logs, exceptions
│   └── ml/
│       ├── train.py      # Entraînement + sauvegarde joblib
│       ├── predict.py    # Prédictions
│       ├── retrain.py    # Ré-entraînement
│       └── services.py   # load_model, recommend_books, train_model
├── artifacts/
│   ├── vectorizer.pkl
│   ├── dataframe.pkl
│   └── model.pkl
├── requirements.txt
└── .env
```

## Installation

```bash
cd ml_service
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # puis éditer DATABASE_URL
```

Utilisez la **même** `DATABASE_URL` que Django (`bibliotheque/.env`).

## Entraînement initial

```bash
# CLI
python -m app.ml.train

# ou via API (serveur démarré)
curl -X POST http://localhost:8001/train
```

## Lancement

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

- Swagger : http://localhost:8001/docs  
- ReDoc : http://localhost:8001/redoc  

## Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/health` | Santé API + modèle |
| GET | `/recommendations/{user_id}` | Recommandations personnalisées |
| GET | `/recommendations/similar/{book_id}` | Livres similaires |
| POST | `/train` | Ré-entraînement complet |

### Exemple réponse

```json
{
  "user_id": 12,
  "recommendations": [
    {
      "id": 4,
      "title": "Deep Learning avec Python",
      "author": "François Chollet",
      "category": "informatique",
      "score": 0.95,
      "cover_url": "http://127.0.0.1:8000/media/book_covers/cover_4.jpg"
    }
  ],
  "model_version": "20260515120000"
}
```

## Intégration Django

Dans `bibliotheque/.env` :

```env
RECOMMENDATION_SERVICE_URL=http://localhost:8001
RECOMMENDATION_API_KEY=          # optionnel, même clé que API_KEY du microservice
```

Django appelle automatiquement le microservice via `services.recommandation.ml_client` ; en cas d'indisponibilité, le moteur heuristique local prend le relais.

## Sécurité

- `JWT_ENABLED=true` + `JWT_SECRET_KEY` = secret Django pour valider les tokens SimpleJWT
- ou `API_KEY` / `X-API-Key` pour les appels serveur-à-serveur
- CORS configurable via `CORS_ORIGINS`
- Rate limiting : `RATE_LIMIT=60/minute`

## Production

- Pré-charger le modèle au démarrage (automatique si artefacts présents)
- Planifier `POST /train` (cron) après imports massifs d'emprunts
- Servir derrière un reverse proxy (nginx) avec HTTPS
