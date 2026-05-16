"""Vues d'administration web (tableau de bord, utilisateurs, emprunts)."""
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.core.paginator import Paginator

from services.emprunts.models import Loan
from services.livres.models import Book, Category
from services.analytics.services import get_platform_stats, get_top_books, get_recent_loans
from .decorators import admin_required
from .utils import user_context

User = get_user_model()


def _admin_context(request, **extra):
    return {
        **user_context(request.user),
        "stats": get_platform_stats(),
        **extra,
    }


@admin_required
def admin_dashboard(request):
    return render_admin(request, "backoffice/dashboard.html", {
        "top_books": get_top_books(5),
        "recent_loans": get_recent_loans(8),
    })


@admin_required
def admin_loans(request):
    qs = Loan.objects.select_related("user", "book", "book__category").order_by("-borrowed_at")

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    role = request.GET.get("role", "")
    if role:
        qs = qs.filter(user__role=role)

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(book__title__icontains=search)
            | Q(book__author__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
        )

    overdue_only = request.GET.get("overdue") == "1"
    if overdue_only:
        from django.utils import timezone
        qs = qs.filter(
            status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED, Loan.Status.OVERDUE],
            due_date__lt=timezone.now().date(),
        )

    counts = {
        "all": Loan.objects.count(),
        "active": Loan.objects.filter(status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]).count(),
        "overdue": Loan.objects.filter(status=Loan.Status.OVERDUE).count(),
        "returned": Loan.objects.filter(status=Loan.Status.RETURNED).count(),
    }

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render_admin(request, "backoffice/loans.html", {
        "loans": page_obj,
        "page_obj": page_obj,
        "counts": counts,
        "filter_status": status,
        "filter_role": role,
        "search_query": search,
        "overdue_only": overdue_only,
    })


@admin_required
def admin_users(request):
    qs = User.objects.annotate(
        loan_count=Count("loans"),
        active_loan_count=Count(
            "loans",
            filter=Q(loans__status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]),
        ),
    ).order_by("last_name", "first_name")

    role = request.GET.get("role", "")
    if role:
        qs = qs.filter(role=role)

    active = request.GET.get("active", "")
    if active == "1":
        qs = qs.filter(is_active=True)
    elif active == "0":
        qs = qs.filter(is_active=False)

    has_loans = request.GET.get("has_loans", "")
    if has_loans == "1":
        qs = qs.filter(active_loan_count__gt=0)

    department = request.GET.get("department", "").strip()
    if department:
        qs = qs.filter(department__icontains=department)

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(student_id__icontains=search)
        )

    role_counts = {
        "all": User.objects.count(),
        "student": User.objects.filter(role=User.Role.STUDENT).count(),
        "teacher": User.objects.filter(role=User.Role.TEACHER).count(),
        "staff": User.objects.filter(role=User.Role.STAFF).count(),
        "admin": User.objects.filter(role=User.Role.ADMIN).count(),
    }

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    departments = (
        User.objects.exclude(department__isnull=True)
        .exclude(department="")
        .values_list("department", flat=True)
        .distinct()
        .order_by("department")
    )

    return render_admin(request, "backoffice/users.html", {
        "users": page_obj,
        "page_obj": page_obj,
        "role_counts": role_counts,
        "filter_role": role,
        "filter_active": active,
        "filter_has_loans": has_loans,
        "filter_department": department,
        "search_query": search,
        "departments": departments,
    })


@admin_required
def admin_catalog(request):
    """Catalogue admin : gestion des livres (pas la vue etudiant)."""
    qs = Book.objects.select_related("category").annotate(
        loan_count=Count("loans"),
        active_loan_count=Count(
            "loans",
            filter=Q(loans__status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]),
        ),
    ).order_by("title")

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(author__icontains=search)
            | Q(isbn__icontains=search)
        )

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    availability = request.GET.get("availability")
    if availability == "available":
        qs = qs.filter(available_copies__gt=0)
    elif availability == "unavailable":
        qs = qs.filter(available_copies=0)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render_admin(request, "backoffice/books.html", {
        "books": page_obj,
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "search_query": search,
        "selected_category": category_id,
        "filter_availability": availability,
    })


@admin_required
def admin_recommendations(request):
    """Vue admin : statistiques recommandations (pas la page personnalisee etudiant)."""
    from services.recommandation.services import get_user_recommendations

    top_books = get_top_books(10)
    categories = (
        Category.objects.annotate(book_count=Count("books"))
        .order_by("-book_count")
    )

    sample_students = User.objects.filter(role=User.Role.STUDENT, is_active=True)[:3]
    samples = []
    for student in sample_students:
        recs = get_user_recommendations(student, limit=3)
        if recs:
            samples.append({"user": student, "recommendations": recs})

    return render_admin(request, "backoffice/recommendations.html", {
        "top_books": top_books,
        "categories": categories,
        "sample_recommendations": samples,
        "total_books": Book.objects.count(),
    })


@admin_required
def admin_notifications(request):
    from services.notifications.models import Notification

    qs = Notification.objects.select_related("user").order_by("-created_at")

    ntype = request.GET.get("type", "")
    if ntype:
        qs = qs.filter(type=ntype)

    unread = request.GET.get("unread") == "1"
    if unread:
        qs = qs.filter(is_read=False)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render_admin(request, "backoffice/notifications.html", {
        "notifications": page_obj,
        "page_obj": page_obj,
        "filter_type": ntype,
        "unread_only": unread,
    })


def render_admin(request, template, extra=None):
    from django.shortcuts import render
    ctx = _admin_context(request, **(extra or {}))
    return render(request, template, ctx)
