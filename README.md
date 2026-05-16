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

Ce projet est prêt pour DVC avec :

- un pipeline de production `dvc.yaml`
- des scripts structurés dans `scripts/`
- des données brutes dans `data/raw/`
- des données prétraitées dans `data/processed/`
- un modèle versionné dans `models/model.pkl`
- des métriques sorties dans `metrics/metrics.json`

### Installation DVC

1. Activer ton environnement Python :

```powershell
cd "c:\Users\HP\Desktop\Lybrary_DIT"
python -m pip install -r requirements-dvc.txt
```

2. Supprimer toute configuration DVC antérieure :

```powershell
Remove-Item -Recurse -Force .dvc, .dvcignore, dvc.yaml, dvc.lock, .dvc/cache
```

3. Initialiser DVC dans le dépôt :

```powershell
dvc init
```

4. Ajouter le pipeline propre :

```powershell
dvc repro
```

5. Configurer le remote Google Drive avec service account :

```powershell
dvc remote add -d gdrive gdrive://<FOLDER_ID>
dvc remote modify gdrive gdrive_use_service_account true
dvc remote modify gdrive gdrive_service_account_json_file_path /path/to/service-account.json
```

6. Vérifier le remote :

```powershell
dvc remote list
```

7. Protéger la configuration locale et les accès :

```powershell
Add-Content .gitignore ".dvc/config.local"
Add-Content .gitignore ".dvc/credentials.json"
```

### Utilisation DVC

Pour générer le pipeline complet :

```powershell
dvc repro
```

Pour envoyer les artefacts sur Google Drive :

```powershell
dvc push
```

Pour récupérer une version distante :

```powershell
dvc pull
```

### DVC dans Docker

- Tu peux installer DVC sur l'hôte ou dans le container ML.
- Si tu veux exécuter DVC depuis le container ML, ajoute `dvc[gdrive]` et `PyYAML` dans le Dockerfile ML ou dans un fichier de dépendances partagé.
- Exemple de modification Dockerfile ML :

```dockerfile
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements-dvc.txt \
    && rm /tmp/requirements.txt /tmp/requirements-dvc.txt
```

- Dans `docker-compose.yml`, assure-toi que le volume du projet est monté et que le container peut écrire dans `data/`, `models/`, `metrics/`.

- Tu peux exécuter le pipeline dans Docker avec :

```powershell
docker compose run --rm ml-service python scripts/export_loans.py
```

- Pour utiliser DVC dans le même container :

```powershell
docker compose run --rm ml-service dvc repro
```

### Bonnes pratiques avant DVC

- versionner le code, pas les données lourdes
- garder `.env` hors du dépôt
- utiliser `params.yaml` pour les hyperparamètres
- utiliser `dvc.lock` pour figer les versions du pipeline

## À ne pas versionner

- secrets / fichiers `.env`
- virtualenv local (`env/`)
- bases de données locales (`db.sqlite3`)
- datasets / modèles lourds
- fichiers de build Docker temporaires
