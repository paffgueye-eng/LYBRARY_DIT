from django.core.management.base import BaseCommand
from services.notifications.services import send_loan_reminders, send_overdue_notifications


class Command(BaseCommand):
    help = "Met à jour les statuts d'emprunts et envoie les notifications."

    def handle(self, *args, **options):
        send_loan_reminders()
        send_overdue_notifications()
        self.stdout.write(self.style.SUCCESS("Statuts et notifications synchronisés."))
