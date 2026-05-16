from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Notification


def notify(user, type_, title, message, link=""):
    return Notification.objects.create(
        user=user, type=type_, title=title, message=message, link=link
    )


def send_loan_reminders():
    """Notify users before due date."""
    from services.emprunts.models import Loan

    reminder_days = getattr(settings, "LOAN_REMINDER_DAYS_BEFORE", 2)
    target_date = timezone.now().date() + timedelta(days=reminder_days)

    loans = Loan.objects.filter(
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED],
        due_date=target_date,
    ).select_related("user", "book")

    for loan in loans:
        exists = Notification.objects.filter(
            user=loan.user,
            type=Notification.Type.LOAN_REMINDER,
            title__contains=loan.book.title,
            created_at__date=timezone.now().date(),
        ).exists()
        if not exists:
            notify(
                loan.user,
                Notification.Type.LOAN_REMINDER,
                f"Retour prévu : {loan.book.title}",
                f"Votre livre « {loan.book.title} » doit être retourné le "
                f"{loan.due_date.strftime('%d/%m/%Y')}.",
                link="/loans/",
            )


def send_overdue_notifications():
    from services.emprunts.models import Loan

    overdue = Loan.objects.filter(
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED],
        due_date__lt=timezone.now().date(),
    ).select_related("user", "book")

    for loan in overdue:
        if loan.status != Loan.Status.OVERDUE:
            loan.status = Loan.Status.OVERDUE
            loan.save(update_fields=["status"])
        notify(
            loan.user,
            Notification.Type.LOAN_OVERDUE,
            f"Retard : {loan.book.title}",
            f"L'emprunt de « {loan.book.title} » est en retard de "
            f"{loan.days_overdue} jour(s).",
            link="/loans/",
        )


def notify_recommendations(user, books):
    if not books:
        return
    titles = ", ".join(b.title for b in books[:3])
    notify(
        user,
        Notification.Type.RECOMMENDATION,
        "Nouvelles recommandations pour vous",
        f"Découvrez : {titles} et plus encore.",
        link="/recommendations/",
    )


def notify_reservation_ready(user, book):
    notify(
        user,
        Notification.Type.RESERVATION,
        f"Disponible : {book.title}",
        f"Le livre « {book.title} » que vous avez réservé est maintenant disponible.",
        link=f"/books/{book.id}/",
    )
