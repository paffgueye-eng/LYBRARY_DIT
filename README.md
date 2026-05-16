# Lybrary_DIT

Modern digital library platform for DIT featuring Django REST API, PostgreSQL, Dockerized microservices, and AI-powered book recommendation system.

## Description

Cette application est une plateforme de bibliothèque en ligne pour le DIT. Elle gère les livres, les emprunts, les utilisateurs et intègre un système de recommandation par Machine Learning.

## Architecture

- Backend Django
- PostgreSQL
- Frontend séparé
- Service de recommandation ML
- Conteneurisation Docker / docker-compose

## Démarrage local

1. Copier `.env.example` en `.env` (ou `.env.dev`).
2. Vérifier les variables d’environnement.
3. Lancer les services Docker :

```powershell
docker compose up -d --build
```

4. Vérifier les logs et l’état des containers.

## Commandes utiles

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f ml_service
docker compose down
```

## Bonnes pratiques Git

- Utiliser `main` comme branche principale.
- Faire des commits atomiques.
- Ne jamais versionner les secrets (`.env`, clés, mots de passe).

## Préparation pour DVC

- Ignorer `data/`, `artifacts/`, `models/`, `logs/`.
- Ajouter `.dvcignore` et `.dvc/` après l’installation de DVC.
- Versionner les pipelines mais pas les fichiers binaires lourds.

## À ne pas versionner

- secrets / fichiers `.env`
- virtualenv local (`env/`)
- bases de données locales (`db.sqlite3`)
- datasets / modèles lourds
- fichiers de build Docker temporaires
