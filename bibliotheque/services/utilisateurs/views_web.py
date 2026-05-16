"""
Vues web HTML — imports légers (pas de DRF) pour des temps de réponse rapides.
"""
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from django.contrib.auth import get_user_model

from .utils import user_context

User = get_user_model()

# Chemins sans contexte lourd (voir context_processors)
AUTH_TEMPLATE = "login.html"


def index_page(request):
    from django.db.models import Q
    from services.emprunts.models import Loan
    from services.livres.models import Book, Category

    books_qs = Book.objects.select_related("category").order_by("-created_at")
    with_cover = books_qs.exclude(Q(cover="") | Q(cover__isnull=True))

    featured_books = list(with_cover[:3])
    if len(featured_books) < 3:
        featured_books = list(books_qs[:3])

    showcase_books = list(with_cover[:12])
    if len(showcase_books) < 8:
        showcase_books = list(books_qs[:12])

    active_loans = Loan.objects.filter(
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED, Loan.Status.OVERDUE]
    ).count()

    return render(request, "index.html", {
        "total_books": books_qs.count(),
        "available_books": books_qs.filter(available_copies__gt=0).count(),
        "total_users": User.objects.filter(is_active=True).count(),
        "active_loans": active_loans,
        "featured_books": featured_books,
        "showcase_books": showcase_books,
        "categories": Category.objects.all()[:7],
    })


def login_page(request):
    if request.GET.get("switch") == "1":
        auth_logout(request)

    if request.user.is_authenticated and request.GET.get("switch") != "1":
        if getattr(request.user, "role", None) in ("admin", "staff"):
            return redirect("admin_dashboard")
        return redirect("user_home")

    error_message = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            if user.role in ("admin", "staff"):
                return redirect("admin_dashboard")
            return redirect("user_home")
        error_message = "Adresse e-mail ou mot de passe incorrect."

    return render(request, AUTH_TEMPLATE, {
        "error_message": error_message,
    })


def logout_view(request):
    auth_logout(request)
    return redirect("/login/?fresh=1")




@login_required(login_url="/login/")
def user_home(request):
    from services.emprunts.models import Loan
    from services.livres.models import Book
    from services.recommandation.services import get_user_recommendations

    user = request.user
    active_loans_qs = Loan.objects.filter(
        user=user,
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED, Loan.Status.OVERDUE],
    ).select_related("book", "book__category").order_by("due_date")
    active_loans = active_loans_qs[:5]

    recent_loans = Loan.objects.filter(
        user=user,
        status=Loan.Status.RETURNED,
        returned_at__gte=timezone.now().date() - timezone.timedelta(days=30),
    ).select_related("book", "book__category").order_by("-returned_at")[:10]

    recommendations = get_user_recommendations(user, limit=6)
    latest_books = Book.objects.select_related("category").order_by("-created_at")[:8]
    overdue_count = active_loans_qs.filter(status=Loan.Status.OVERDUE).count()

    context = {
        **user_context(user),
        "user_name": user.first_name or user.email.split("@")[0],
        "user_department": user.department or "",
        "active_loans": active_loans,
        "recent_loans": recent_loans,
        "recommendations": recommendations,
        "latest_books": latest_books,
        "total_loans": Loan.objects.filter(user=user).count(),
        "active_loans_count": active_loans_qs.count(),
        "overdue_count": overdue_count,
    }
    return render(request, "user/home.html", context)


@login_required(login_url="/login/")
def profile_page(request):
    from services.emprunts.models import Loan
    from services.livres.models import Favorite

    user = request.user
    favorites = Favorite.objects.filter(user=user).select_related("book")[:12]
    recent_loans = Loan.objects.filter(user=user).select_related(
        "book", "book__category"
    ).order_by("-created_at")[:8]
    total_loans = Loan.objects.filter(user=user).count()
    active_loans = Loan.objects.filter(
        user=user, status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]
    ).count()

    context = {
        **user_context(user),
        "user_name": user.first_name or user.email.split("@")[0],
        "user_email": user.email,
        "user_student_id": user.student_id or "",
        "user_bio": user.bio or "",
        "user_joined": user.date_joined,
        "favorites": favorites,
        "recent_loans": recent_loans,
        "total_loans": total_loans,
        "active_loans": active_loans,
    }

    template_name = "user/profile.html"
    if getattr(user, "role", None) in ("admin", "staff"):
        template_name = "backoffice/profile.html"

    return render(request, template_name, context)
