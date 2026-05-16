
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


