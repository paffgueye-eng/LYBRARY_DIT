# Lybrary_DIT — README 

Projet de plateforme de bibliothèque numérique pour le Dakar Institute of Technology (DIT).
Ce dépôt contient un backend Django, des microservices ML (FastAPI), une orchestration Docker Compose,
un pipeline DVC pour les données et des artefacts ML, ainsi qu’un frontend statique servi par NGINX.

Table des matières
- Présentation
- Architecture et composants
- Prérequis
- Variables d'environnement & Secrets
- Démarrage local (Docker)
- Développement local (sans Docker)
- DVC (pipeline data & modèles)
- Tests et qualité
- CI/CD (GitHub Actions)
- Publication d'images (GHCR)
- Dépannage & logs
- Notes Windows / Docker Desktop
- Contribution
- Licence

Présentation
------------
Lybrary_DIT est une application modulaire pour gérer un catalogue de livres, les emprunts, les utilisateurs
et fournir des recommandations basées sur un pipeline ML. Le projet est prêt pour des workflows DevOps/MLOps.

Architecture et composants
---------------------------
- `bibliotheque/` : backend Django (API REST + pages admin)
- `ml_service/` : microservice ML (FastAPI) et scripts d'entraînement
- `docker-compose.yml` : orchestration des services locaux
- `Dockerfile.django`, `Dockerfile.reco`, `Dockerfile.ml`, `Dockerfile.frontend` : images de chaque service
- `dvc.yaml`, `requirements-dvc.txt` : pipeline DVC et dépendances data-science
- `scripts/` : scripts utilitaires (`export_loans.py`, `preprocess.py`, `train.py`, `evaluate.py`)
- `data/`, `models/`, `metrics/` : lieux pour données, artefacts et métriques

Prérequis
---------
- Git
- Docker Desktop (Windows) ou Docker Engine (Linux/macOS)
- Docker Compose (v2+) — `docker compose` CLI
- Python 3.10 (pour exécuter localement hors conteneur)
- DVC (optionnel, pour pipeline data)

Variables d'environnement & Secrets
----------------------------------
Ajouter dans un fichier `.env` non versionné (ex. copier `.env.example` → `.env`) ou définir en CI via secrets.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL` (optionnel, format `postgres://user:pass@host:port/db`)
- `RECOMMENDATION_API_KEY` (si utilisé)
- `RECOMMENDATION_SERVICE_URL` (par défaut `http://localhost:8001`)
- Pour DVC remote: `DVC_REMOTE_URL` et credentials appropriés (ex: JSON service account pour Google Drive)

Démarrage local — Docker (recommandé)
----------------------------------
1. Copier l'exemple d'environnement et adapter les secrets :

```powershell
cd "c:\Users\HP\Desktop\Lybrary_DIT"
copy .env.example .env
# Éditez .env
```

2. Construire et lancer les services en arrière-plan :

```powershell
docker compose up -d --build
```

3. Vérifier l'état des services :

```powershell
docker compose ps
docker compose logs -f dit_django
```

4. Points d'accès par défaut :
- Backend Django : `http://localhost:8000`
- Reco API docs (FastAPI) : `http://localhost:8001/docs`
- Frontend (NGINX) : `http://localhost:3000`

Développement local (sans Docker)
--------------------------------
1. Créer et activer un venv Python 3.12 :

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

2. Installer dépendances :

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Configurer la base (ex: SQLite ou `DATABASE_URL`) et lancer migrations :

```powershell
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

DVC — pipeline data & modèles
------------------------------
Le pipeline DVC est défini dans `dvc.yaml` (stages: export, preprocess, train, evaluate).

Exemples de commandes DVC :

```bash
pip install -r requirements-dvc.txt
# Récupérer les données distante (si remote configuré)
dvc pull
# Exécuter le pipeline localement
dvc repro
# Pousser artefacts vers le remote
dvc push
```

Si tu préfères exécuter DVC dans le conteneur ML, installe `dvc[gdrive]` dans l'image ML ou utilise le job DVC du CI.

Tests et qualité
----------------
- Tests Django : `python manage.py test`
- Tu peux ajouter `flake8`, `mypy` ou `pytest` selon préférence. Le workflow CI inclut l’exécution des tests Django sur Linux et Windows.

CI/CD — GitHub Actions
-----------------------
Un workflow GitHub Actions a été ajouté dans `.github/workflows/ci.yml` avec :
- Job `tests` : installe les dépendances et exécute les tests Django en matrice (`ubuntu-latest`, `windows-latest`).
- Job `docker-compose-deploy` : build des images, `docker compose up -d`, vérifications smoke (endpoints) et collecte des logs en cas d'échec.
- Job `dvc-repro` : installe `requirements-dvc.txt`, configure le remote DVC (optionnel), `dvc pull` puis `dvc repro`, et upload des métriques.
- Job `publish` : construction et push des images vers GHCR (GitHub Container Registry). Configure `GHCR_TOKEN` dans les secrets pour publier.

Publication d’images (GHCR)
---------------------------
Le job `publish` construit et publie les images Docker sur GHCR ; tu peux configurer `GHCR_TOKEN` dans les secrets du dépôt.
Si tu préfères Docker Hub, je peux ajouter un job alternatif qui se logue sur Docker Hub et pousse les images.

Dépannage & logs
----------------
- En cas d’échec des healthchecks, consulte les logs :

```powershell
docker compose logs --no-color > compose-logs.txt
cat compose-logs.txt
```

- Pour les erreurs Django : `docker compose logs dit_django` ou `docker compose exec dit_django bash` puis inspecte `/app/logs`.
- En CI, les logs sont uploadés comme artefacts quand une étape échoue (voir `compose-logs`).

Notes Windows / Docker Desktop
------------------------------
- Le workflow CI exécute les tests unitaires sur `windows-latest` mais exécute Docker Compose sur `ubuntu-latest` (runners Windows hébergés ne fournissent pas Docker Desktop prêt à l’emploi).
- Pour CI Docker sur Windows, utilise un runner self-hosted Windows avec Docker Desktop installé.

Contribution
------------
1. Fork → branche feature → PR with description and tests.
2. Respecte les conventions de commit et ajoute des tests pour tout nouveau comportement.

Push vers remote 
--------------------------
Après avoir vérifié localement, pousse tes changements :

```bash
git add .
git commit -m "feat(ci): add GitHub Actions CI + DVC + publish jobs; add README"
git push origin main
```
