from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        LOAN_REMINDER = "loan_reminder", "Rappel de retour"
        LOAN_OVERDUE = "loan_overdue", "Emprunt en retard"
        RECOMMENDATION = "recommendation", "Nouvelle recommandation"
        RESERVATION = "reservation", "Réservation disponible"
        ACCOUNT = "account", "Activité du compte"
        SYSTEM = "system", "Système"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.user} – {self.title}"
