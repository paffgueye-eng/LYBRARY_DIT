from fastapi import HTTPException, status


class ModelNotReadyError(Exception):
    """Raised when ML artifacts are missing or invalid."""


class UserNotFoundError(Exception):
    """Raised when the user id does not exist."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Utilisateur {user_id} introuvable.")


def http_model_not_ready() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Le modèle IA n'est pas encore entraîné. Appelez POST /train.",
    )


def http_user_not_found(user_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Utilisateur {user_id} introuvable.",
    )
