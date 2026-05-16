"""
API REST (DRF) — les vues web HTML sont dans views_web.py.
"""
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view

from .permissions import IsAdminUser, IsOwnerOrAdmin
from .serializers import (
    ChangePasswordSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)

# Réexport des vues web (compatibilité imports existants)
from .views_web import (  # noqa: E402, F401
    index_page,
    login_page,
    logout_view,
    profile_page,
    user_home,
)

User = get_user_model()


@extend_schema_view(
    list=extend_schema(tags=["users"], summary="Lister tous les utilisateurs"),
    retrieve=extend_schema(tags=["users"], summary="Détail d'un utilisateur"),
    create=extend_schema(tags=["users"], summary="Créer un utilisateur"),
    update=extend_schema(tags=["users"], summary="Modifier un utilisateur"),
    partial_update=extend_schema(tags=["users"], summary="Modifier partiellement un utilisateur"),
    destroy=extend_schema(tags=["users"], summary="Supprimer un utilisateur"),
)
class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("last_name")
    search_fields = ["email", "first_name", "last_name", "student_id"]
    filterset_fields = ["role", "is_active", "department"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("retrieve", "update", "partial_update", "me"):
            return UserDetailSerializer
        return UserListSerializer

    def get_permissions(self):
        if self.action == "create":
            if self.request.data.get("public_register"):
                return [permissions.AllowAny()]
            return [IsAdminUser()]
        if self.action in ("update", "partial_update"):
            return [IsOwnerOrAdmin()]
        if self.action == "destroy":
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @extend_schema(tags=["users"], summary="Mon profil")
    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        if request.method == "GET":
            serializer = UserDetailSerializer(request.user)
            return Response(serializer.data)

        serializer = UserDetailSerializer(
            request.user, data=request.data, partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(tags=["users"], summary="Changer mon mot de passe")
    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Mot de passe mis à jour avec succès."})

    @extend_schema(tags=["users"], summary="Activer / désactiver un compte")
    @action(detail=True, methods=["post"], url_path="toggle-active", permission_classes=[IsAdminUser])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        state = "activé" if user.is_active else "désactivé"
        return Response({"detail": f"Compte {state}.", "is_active": user.is_active})


from .admin_views import (  # noqa: F401
    admin_catalog,
    admin_dashboard,
    admin_loans,
    admin_notifications,
    admin_recommendations,
    admin_users,
)
