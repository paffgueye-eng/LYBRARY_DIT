"""
apps/users/permissions.py
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

#IsAdminUser admin seulement
class IsAdminUser(BasePermission):
    """Only users with role='admin' (not just is_staff)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)

#IsOwnerOrAdmin propriétaire OU admin
#Lutilisateur peut modifier son propre profil mais pas celui des autres
#Admin peut tout modifier 
class IsOwnerOrAdmin(BasePermission):
    """Allow object access to its owner or an admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin: #si le requeteur est admin donne lui tous les autorisation 
            return True
        return obj == request.user #On compare lobject demander avec lutilisateur qui effectue cette requete

#IsAdminOrReadOnly Tous les utilisateurs connectés peuvent lire.
# Seuls les admins peuvent modifier.
class IsAdminOrReadOnly(BasePermission):
    """Read-only for authenticated users; write requires admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin
