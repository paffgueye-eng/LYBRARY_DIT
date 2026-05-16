from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate users by email instead of username."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identifier = email or username
        if identifier is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
