# DVC Setup propre pour Lybrary_DIT

Ce document décrit les étapes pour repartir de zéro avec DVC, configurer un remote Google Drive avec service account et exécuter un pipeline MLOps reproductible.

## 1. Reset / Clean DVC

Ne supprimez pas `dvc.yaml` ni `.dvcignore` : le pipeline DVC existant est valide.
Supprimez seulement l’état DVC ancien / cassé :

```powershell
cd "c:\Users\HP\Desktop\Lybrary_DIT"
Remove-Item -Recurse -Force .dvc, dvc.lock, .dvc/config.local, .dvc/cache, .dvc/tmp -ErrorAction SilentlyContinue
```

### Nettoyage de cache DVC

```powershell
Remove-Item -Recurse -Force .dvc/cache -ErrorAction SilentlyContinue
```

> Remarque : `.dvc/config.local` n’est pas versionné, donc il est propre de le supprimer si on veut repartir totalement à zéro.

## 2. Réinitialisation DVC propre

1. Installer les dépendances DVC :

```powershell
python -m pip install -r requirements-dvc.txt
```

2. Initialiser DVC :

```powershell
python -m dvc init --force
```

3. Vérifier que le dossier `.dvc/` existe et que le fichier `.dvcignore` est propre.

4. Vérifier que `dvc.yaml` contient le pipeline : export → preprocess → train → evaluate.

## 3. Configuration remote Google Drive (service account)

1. Créer le remote DVC :

```powershell
python -m dvc remote add -d gdrive gdrive://<FOLDER_ID>
```

2. Activer le service account :

```powershell
python -m dvc remote modify gdrive gdrive_use_service_account true
```

3. Spécifier le fichier JSON du service account :

```powershell
python -m dvc remote modify gdrive gdrive_service_account_json_file_path C:\path\to\service-account.json --local
```

4. Vérifier la configuration :

```powershell
python -m dvc remote list
```

### Attention

- Le fichier de clé service account ne doit jamais être commité.
- Garder `.dvc/config.local` et le fichier JSON en dehors du dépôt.
- `.dvc/config.local.example` contient un exemple de configuration dans le repo.

## 4. Export data PostgreSQL

Le script existant `scripts/export_loans.py` est structuré pour :

- lire `DATABASE_URL` depuis `.env` ou `--database-url`
- se connecter à PostgreSQL avec SQLAlchemy
- exporter `data/raw/loans.csv`

Exemple :

```powershell
python scripts/export_loans.py --output data/raw/loans.csv --database-url "postgresql://user:pass@host:5432/dbname"
```

## 5. Pipeline DVC complet

Le pipeline est défini dans `dvc.yaml` :

- `export` → `data/raw/loans.csv`
- `preprocess` → `data/processed/loans_clean.csv`
- `train` → `models/model.pkl`
- `evaluate` → `metrics/metrics.json`

### Exécution du pipeline

```powershell
python -m dvc repro
```

Sur Docker :

```powershell
docker compose run --rm dvc-runner bash -lc "pip install -r requirements-dvc.txt && python -m dvc repro"
```

## 6. Versioning propre

### Fichiers importants à garder dans Git

- `dvc.yaml`
- `dvc.lock`
- `.dvcignore`
- `params.yaml`
- scripts Python
- `.gitignore`

### Suivi des données et modèles

- Avec DVC, les artefacts sont gérés via les sorties de `dvc.yaml`.
- Si un fichier doit être versionné indépendamment, utilisez :

```powershell
python -m dvc add data/raw/loans.csv
```

- `python -m dvc repro` reconstruira le pipeline et mettra à jour `dvc.lock`.

### Rôle de `dvc.lock`

- fixe les versions exactes des commandes, dépendances et sorties
- permet de reproduire le même pipeline plus tard
- doit être versionné avec Git

## 7. Metrics

Le stage `evaluate` produit `metrics/metrics.json`.

Pour afficher les métriques actuelles :

```powershell
python -m dvc metrics show
```

Pour comparer avec la version précédente :

```powershell
python -m dvc metrics diff
```

## 8. Docker + DVC integration

Ce projet possède un service `dvc-runner` dans `docker-compose.yml`.

Exemple d’exécution :

```powershell
docker compose run --rm dvc-runner bash -lc "pip install -r requirements-dvc.txt && python -m dvc repro"
```

Pour pousser vers le remote depuis Docker :

```powershell
docker compose run --rm dvc-runner bash -lc "pip install -r requirements-dvc.txt && python -m dvc push"
```

Pour récupérer depuis le remote :

```powershell
docker compose run --rm dvc-runner bash -lc "pip install -r requirements-dvc.txt && python -m dvc pull"
```

## 9. Intégration Django

Pour charger le modèle IA dans Django :

1. Ajouter un chemin configurable dans `settings.py` ou `env` :

```python
MODEL_PATH = BASE_DIR / "models" / "model.pkl"
```

2. Charger le modèle avec `joblib` :

```python
import joblib
from django.conf import settings

model = joblib.load(settings.MODEL_PATH)
```

3. Utiliser `model.predict(user_id, book_id)` dans l’API.

### Versioning modèle IA

- le modèle est versionné par DVC via `models/model.pkl`
- `python -m dvc repro` reconstruit le modèle à chaque changement de données ou code
- `python -m dvc push` envoie les artefacts vers le remote
- `python -m dvc pull` récupère la version distante à l’exécution

## 10. Résultat final attendu

- un DVC propre et réinitialisé
- un pipeline reproductible
- un remote Google Drive prêt à être configuré
- une intégration Docker-compatible
- une base prête pour production MLOps


Arborescence minimale :

- `.dvcignore`
- `dvc.yaml`
- `dvc.lock`
- `.dvc/`
- `params.yaml`
- `scripts/export_loans.py`
- `scripts/preprocess.py`
- `scripts/train.py`
- `scripts/evaluate.py`
- `data/raw/loans.csv`
- `data/processed/loans_clean.csv`
- `models/model.pkl`
- `metrics/metrics.json`

Commandes terminal principales :

```powershell
python -m pip install -r requirements-dvc.txt
dvc init
dvc repro
dvc push
dvc pull
dvc metrics show
dvc metrics diff
```

> L’objectif est un pipeline DVC propre, reproductible et indépendant des conflits Docker/DVC.
