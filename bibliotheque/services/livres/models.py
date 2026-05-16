from django.db import models

# Create your models here.
"""
apps/books/models.py
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Catégorie")
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name        = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering            = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    """Central book record in the catalogue."""

    # ── Bibliographic info ────────────────────────────────────
    title       = models.CharField(max_length=300, verbose_name="Titre")
    author      = models.CharField(max_length=200, verbose_name="Auteur(s)")
    isbn        = models.CharField(
        max_length=17, unique=True, verbose_name="ISBN",
        help_text="Format: 978-X-XXXXX-XXX-X"
    )
    publisher   = models.CharField(max_length=200, blank=True, verbose_name="Éditeur")
    year        = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Année de publication"
    )
    pages       = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nombre de pages")
    language    = models.CharField(max_length=30, default="Français", verbose_name="Langue")
    description = models.TextField(blank=True, verbose_name="Description")
    cover       = models.ImageField(
        upload_to="book_covers/", null=True, blank=True, verbose_name="Couverture"
    )

    # ── Classification ────────────────────────────────────────
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="books", verbose_name="Catégorie"
    )
    keywords    = models.CharField(
        max_length=300, blank=True,
        verbose_name="Mots-clés", help_text="Séparés par des virgules"
    )

    # ── Inventory ─────────────────────────────────────────────
    total_copies     = models.PositiveIntegerField(default=1, verbose_name="Nombre total d'exemplaires")
    available_copies = models.PositiveIntegerField(default=1, verbose_name="Exemplaires disponibles")

    # ── Location ──────────────────────────────────────────────
    location    = models.CharField(
        max_length=100, blank=True, verbose_name="Localisation",
        help_text="Ex: DIT Campus – Zone A"
    )
    call_number = models.CharField(max_length=50, blank=True, verbose_name="Numéro de cote")

    # ── Timestamps ────────────────────────────────────────────
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Livre"
        verbose_name_plural = "Livres"
        ordering            = ["title"]
        indexes             = [
            models.Index(fields=["isbn"]),
            models.Index(fields=["author"]),
            models.Index(fields=["title"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.author}"

    @property
    def is_available(self):
        return self.available_copies > 0

    def decrement_copies(self):
        if self.available_copies <= 0:
            raise ValueError("Aucun exemplaire disponible.")
        self.available_copies -= 1
        self.save(update_fields=["available_copies"])

    def increment_copies(self):
        if self.available_copies >= self.total_copies:
            raise ValueError("Tous les exemplaires sont déjà disponibles.")
        self.available_copies += 1
        self.save(update_fields=["available_copies"])


class BookReview(models.Model):
    """User rating and review for a book."""
    book    = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    user    = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="reviews"
    )
    rating  = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note (1–5)"
    )
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ("book", "user")
        verbose_name        = "Avis"
        verbose_name_plural = "Avis lecteurs"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"{self.user} – {self.book.title} ({self.rating}★)"


class Favorite(models.Model):
    """User wishlist / favorites."""
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="favorites"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} ♥ {self.book.title}"
