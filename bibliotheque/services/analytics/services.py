from django.db.models import Count, Sum
from django.utils import timezone

from django.contrib.auth import get_user_model
from services.livres.models import Book, Category
from services.emprunts.models import Loan, Reservation

User = get_user_model()


def get_platform_stats():
    today = timezone.now().date()
    active_loans = Loan.objects.filter(
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]
    )
    overdue_loans = active_loans.filter(due_date__lt=today)

    return {
        "total_books": Book.objects.count(),
        "total_copies": Book.objects.aggregate(total=Sum("total_copies"))["total"] or 0,
        "available_books": Book.objects.filter(available_copies__gt=0).count(),
        "total_users": User.objects.filter(is_active=True).count(),
        "students": User.objects.filter(role=User.Role.STUDENT, is_active=True).count(),
        "teachers": User.objects.filter(role=User.Role.TEACHER, is_active=True).count(),
        "active_loans": active_loans.count(),
        "overdue_loans": overdue_loans.count(),
        "returned_this_month": Loan.objects.filter(
            status=Loan.Status.RETURNED,
            returned_at__gte=today.replace(day=1),
        ).count(),
        "pending_reservations": Reservation.objects.filter(
            status=Reservation.Status.PENDING
        ).count(),
        "categories_count": Category.objects.count(),
    }


def get_top_books(limit=5):
    return (
        Book.objects.annotate(loan_count=Count("loans"))
        .order_by("-loan_count")[:limit]
    )


def get_recent_loans(limit=10):
    return Loan.objects.select_related("user", "book").order_by("-created_at")[:limit]


def get_users_by_role():
    return User.objects.values("role").annotate(count=Count("id")).order_by("role")
