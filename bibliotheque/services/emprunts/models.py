from django.db import models

# Create your models here.
"""
apps/loans/models.py
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def default_due_date():
    days = getattr(settings, "LOAN_DURATION_DAYS", 14)
    return timezone.now().date() + timedelta(days=days)


class Loan(models.Model):
    """Represents a single borrow event (book ↔ user)."""

    class Status(models.TextChoices):
        ACTIVE    = "active",    "En cours"
        RETURNED  = "returned",  "Retourné"
        OVERDUE   = "overdue",   "En retard"
        RENEWED   = "renewed",   "Renouvelé"

    # ── Relations ─────────────────────────────────────────────
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="loans", verbose_name="Emprunteur"
    )
    book        = models.ForeignKey(
        "books.Book", on_delete=models.PROTECT,
        related_name="loans", verbose_name="Livre"
    )

    # ── Dates ─────────────────────────────────────────────────
    borrowed_at = models.DateField(default=timezone.now, verbose_name="Date d'emprunt")
    due_date    = models.DateField(default=default_due_date, verbose_name="Date de retour prévue")
    returned_at = models.DateField(null=True, blank=True, verbose_name="Date de retour effective")

    # ── State ─────────────────────────────────────────────────
    status      = models.CharField(
        max_length=10, choices=Status.choices,
        default=Status.ACTIVE, verbose_name="Statut"
    )
    renewal_count = models.PositiveSmallIntegerField(default=0)
    notes       = models.TextField(blank=True, verbose_name="Notes bibliothécaire")

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Emprunt"
        verbose_name_plural = "Emprunts"
        ordering            = ["-borrowed_at"]
        indexes             = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.book.title} [{self.status}]"

    # ── Computed properties ────────────────────────────────────
    @property
    def is_overdue(self):
        if self.status in (self.Status.RETURNED,):
            return False
        return timezone.now().date() > self.due_date

    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days

    @property
    def days_remaining(self):
        if self.status == self.Status.RETURNED:
            return None
        delta = (self.due_date - timezone.now().date()).days
        return max(delta, 0)

    # ── Business logic ─────────────────────────────────────────
    def mark_returned(self):
        self.returned_at = timezone.now().date()
        self.status = self.Status.RETURNED
        self.save(update_fields=["returned_at", "status"])
        self.book.increment_copies()

    def renew(self, extra_days=None):
        extra_days = extra_days or getattr(settings, "LOAN_DURATION_DAYS", 14)
        self.due_date += timedelta(days=extra_days)
        self.renewal_count += 1
        self.status = self.Status.RENEWED
        self.save(update_fields=["due_date", "renewal_count", "status"])


class Reservation(models.Model):
    """Queue reservation for an unavailable book."""

    class Status(models.TextChoices):
        PENDING   = "pending",   "En attente"
        READY     = "ready",     "Disponible – à récupérer"
        FULFILLED = "fulfilled", "Honorée"
        CANCELLED = "cancelled", "Annulée"

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="reservations"
    )
    book       = models.ForeignKey(
        "books.Book", on_delete=models.CASCADE,
        related_name="reservations"
    )
    status     = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateField(null=True, blank=True)

    class Meta:
        unique_together     = ("user", "book", "status")
        verbose_name        = "Réservation"
        verbose_name_plural = "Réservations"
        ordering            = ["reserved_at"]

    def __str__(self):
        return f"{self.user} ⟳ {self.book.title} [{self.status}]"
