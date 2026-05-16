"""
apps/users/serializers.py
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


# ── Auth ──────────────────────────────────────────────────────────────────────
#Cette classe sert a lauthentification de lutilsateur 
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add user info to the JWT login response.
    simple JWT  plugin dauthentificatin JSON WEB TOKEN
    vérifie email/password
    génère access token
    génère refresh token
      """

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data.update({
            "user": {
                "id":         user.pk,
                "email":      user.email,
                "first_name": user.first_name,
                "last_name":  user.last_name,
                "full_name":  user.full_name,
                "role":       user.role,
                "student_id": user.student_id or "",
                "phone":      user.phone or "",
                "department": user.department or "",
                "bio":        user.bio or "",
                "avatar_url": user.avatar.url if user.avatar else None,
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            }
        })
        return data


# ── User CRUD ─────────────────────────────────────────────────────────────────
#Nous permet de lister plusieurs utilisateurs 
class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = ["id", "email", "full_name", "role", "student_id",
                  "department", "is_active", "date_joined"]

#Nous permet dafficher les information complet des utilisateur
class UserDetailSerializer(serializers.ModelSerializer):
    """Full profile serializer."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "student_id", "phone", "avatar", "department",
            "bio", "is_active", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

#Ce serialiseur transforme les donnees recues en un objet utilsateur dans la base de donnees
class UserCreateSerializer(serializers.ModelSerializer):
    """Registration / admin-create serializer with password hashing."""
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirmation du mot de passe")

    class Meta:
        model  = User
        fields = [
            "email", "first_name", "last_name", "role",
            "student_id", "phone", "department",
            "password", "password2",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError(
                {"password2": "Les mots de passe ne correspondent pas."}
            )
        return attrs
#On utilise create_user au lieu de create. C'est cette méthode de Django qui s'occupe de hasher (crypter) le mot de passe
    def create(self, validated_data):
        validated_data.pop("public_register", None)
        return User.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
#check_password(value) : Utilise la fonction interne de Django pour comparer le mot de passe fourni avec le hash stocké en base de données.
    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value
