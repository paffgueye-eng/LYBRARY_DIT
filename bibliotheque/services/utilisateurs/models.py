from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student", "Étudiant"
        TEACHER = "teacher", "Professeur"
        STAFF = "staff", "Personnel"
        ADMIN = "admin", "Administrateur"

    email = models.EmailField(unique=True, verbose_name="Adresse e-mail")
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="Rôle",
    )
    student_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Numéro étudiant")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Téléphone")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="Avatar")
    department = models.CharField(max_length=120, blank=True, null=True, verbose_name="Département")
    bio = models.TextField(blank=True, null=True, verbose_name="Bio")
    is_staff = models.BooleanField(default=False, verbose_name="Personnel")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Date d'inscription")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def initials(self):
        parts = (
            (self.first_name[:1] if self.first_name else "") +
            (self.last_name[:1] if self.last_name else "")
        ).upper()
        return parts or (self.email[:2].upper() if self.email else "U")

    def __str__(self):
        return self.full_name or self.email
