from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
import csv
from datetime import date

from services.utilisateurs.permissions import IsAdminUser
from services.livres.models import Book
from .models import Loan, Reservation
from .serializers import (
    LoanCreateSerializer, LoanDetailSerializer,
    LoanListSerializer, ReservationSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["loans"], summary="Lister les emprunts"),
    retrieve=extend_schema(tags=["loans"], summary="Détail d'un emprunt"),
    create=extend_schema(tags=["loans"], summary="Créer un emprunt"),
    destroy=extend_schema(tags=["loans"], summary="Annuler un emprunt (admin)"),
)
class LoanViewSet(viewsets.ModelViewSet):
    """
    Manage the full loan lifecycle.
    Regular users see only their own loans.
    Admins see all.
    """
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ["borrowed_at", "due_date", "status"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Loan.objects.select_related("user", "book", "book__category").all()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.order_by("-borrowed_at")

    def get_serializer_class(self):
        if self.action == "create":
            return LoanCreateSerializer
        if self.action == "retrieve":
            return LoanDetailSerializer
        return LoanListSerializer

    @extend_schema(tags=["loans"], summary="Retourner un livre")
    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        loan = self.get_object()
        if loan.status == Loan.Status.RETURNED:
            return Response(
                {"detail": "Ce livre a déjà été retourné."},
                status=status.HTTP_400_BAD_REQUEST
            )
        loan.mark_returned()
        return Response(LoanDetailSerializer(loan).data)

    @extend_schema(tags=["loans"], summary="Renouveler un emprunt")
    @action(detail=True, methods=["post"], url_path="renew")
    def renew_loan(self, request, pk=None):
        loan = self.get_object()
        MAX_RENEWALS = 2
        if loan.renewal_count >= MAX_RENEWALS:
            return Response(
                {"detail": f"Limite de renouvellements atteinte ({MAX_RENEWALS})."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if loan.status == Loan.Status.RETURNED:
            return Response(
                {"detail": "Impossible de renouveler un livre retourné."},
                status=status.HTTP_400_BAD_REQUEST
            )
        loan.renew()
        return Response(LoanDetailSerializer(loan).data)

    @extend_schema(tags=["loans"], summary="Emprunts en retard")
    @action(detail=False, methods=["get"], url_path="overdue",
            permission_classes=[IsAdminUser])
    def overdue(self, request):
        """Lister tous les emprunts en retard (admin)."""
        overdue_loans = Loan.objects.filter(
            status=Loan.Status.ACTIVE,
            due_date__lt=timezone.now().date()
        ).select_related("user", "book")
        page = self.paginate_queryset(overdue_loans)
        if page is not None:
            return self.get_paginated_response(LoanListSerializer(page, many=True).data)
        return Response(LoanListSerializer(overdue_loans, many=True).data)

    @extend_schema(tags=["loans"], summary="Mes emprunts actifs")
    @action(detail=False, methods=["get"], url_path="my-active")
    def my_active(self, request):
        """Lister les emprunts actifs de l'utilisateur courant."""
        active_loans = Loan.objects.filter(
            user=request.user,
            status=Loan.Status.ACTIVE
        ).select_related("book")
        page = self.paginate_queryset(active_loans)
        if page is not None:
            return self.get_paginated_response(LoanListSerializer(page, many=True).data)
        return Response(LoanListSerializer(active_loans, many=True).data)

    @extend_schema(
        tags=["loans"],
        summary="Exporter l'historique en CSV (ML)",
        parameters=[
            OpenApiParameter("from_date", str, description="YYYY-MM-DD"),
            OpenApiParameter("to_date", str, description="YYYY-MM-DD"),
        ]
    )
    @action(detail=False, methods=["get"], url_path="export/csv",
            permission_classes=[IsAdminUser])
    def export_csv(self, request):
        """Export full loan history as CSV for ML training."""
        qs = Loan.objects.select_related("user", "book", "book__category").filter(
            status=Loan.Status.RETURNED
        )
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        if from_date:
            qs = qs.filter(borrowed_at__gte=from_date)
        if to_date:
            qs = qs.filter(borrowed_at__lte=to_date)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="dit_loans_history_{date.today()}.csv"'
        )
        response.write("\ufeff")  # BOM for Excel UTF-8

        writer = csv.writer(response)
        writer.writerow([
            "loan_id", "user_id", "user_role",
            "book_id", "book_title", "book_author",
            "category", "isbn",
            "borrowed_at", "due_date", "returned_at",
            "days_borrowed", "was_overdue", "renewal_count",
        ])

        for loan in qs:
            days = (loan.returned_at - loan.borrowed_at).days if loan.returned_at else None
            writer.writerow([
                loan.id,
                loan.user_id,
                loan.user.role,
                loan.book_id,
                loan.book.title,
                loan.book.author,
                loan.book.category.name if loan.book.category else "",
                loan.book.isbn,
                loan.borrowed_at,
                loan.due_date,
                loan.returned_at,
                days,
                loan.returned_at and loan.returned_at > loan.due_date,
                loan.renewal_count,
            ])
        return response


@extend_schema_view(
    list=extend_schema(tags=["reservations"], summary="Lister les réservations"),
    retrieve=extend_schema(tags=["reservations"], summary="Détail d'une réservation"),
    create=extend_schema(tags=["reservations"], summary="Créer une réservation"),
    destroy=extend_schema(tags=["reservations"], summary="Annuler une réservation"),
)
class ReservationViewSet(viewsets.ModelViewSet):
    """Gestion des réservations de livres."""
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Reservation.objects.select_related("user", "book").all()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs.order_by("reserved_at")

    def create(self, request, *args, **kwargs):
        """Créer une réservation."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@login_required(login_url='/login/')
def my_loans(request):
    """Mes emprunts - vue pour tous les utilisateurs authentifiés."""
    search_query = request.GET.get('search', '').strip()

    active_loans = Loan.objects.filter(
        user=request.user,
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED, Loan.Status.OVERDUE]
    ).select_related("book", "book__category").order_by("due_date")

    recent_loans = Loan.objects.filter(
        user=request.user,
        status=Loan.Status.RETURNED,
        returned_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).select_related("book", "book__category").order_by("-returned_at")[:10]

    reservations = Reservation.objects.filter(
        user=request.user,
        status=Reservation.Status.PENDING
    ).select_related("book", "book__category").order_by("reserved_at")

    if search_query:
        query = Q(book__title__icontains=search_query) | Q(book__author__icontains=search_query) | Q(book__isbn__icontains=search_query)
        active_loans = active_loans.filter(query)
        recent_loans = recent_loans.filter(query)
        reservations = reservations.filter(query)

    total_loans = Loan.objects.filter(user=request.user).count()
    active_count = active_loans.count()
    renewed_count = active_loans.filter(status=Loan.Status.RENEWED).count()
    overdue_count = active_loans.filter(due_date__lt=timezone.now().date()).count()
    returned_count = Loan.objects.filter(user=request.user, status=Loan.Status.RETURNED).count()

    # Recommandations basées sur les catégories de vos emprunts en cours.
    category_ids = active_loans.values_list('book__category_id', flat=True).distinct()
    recommended_books = Book.objects.filter(available_copies__gt=0)
    if category_ids:
        recommended_books = recommended_books.filter(category_id__in=category_ids)

    recommended_books = recommended_books.exclude(
        id__in=active_loans.values_list('book_id', flat=True)
    ).order_by('-available_copies')[:6]

    if not recommended_books.exists():
        recommended_books = Book.objects.filter(
            available_copies__gt=0
        ).exclude(
            id__in=active_loans.values_list('book_id', flat=True)
        ).order_by('-available_copies')[:6]

    context = {
        'active_loans': active_loans,
        'recent_loans': recent_loans,
        'reservations': reservations,
        'recommended_books': recommended_books,
        'total_loans': total_loans,
        'active_count': active_count,
        'renewed_count': renewed_count,
        'overdue_count': overdue_count,
        'returned_count': returned_count,
        'search_query': search_query,
        'user_full_name': request.user.full_name or request.user.email,
        'user_role': request.user.get_role_display(),
        'user_initials': (request.user.first_name[:1] + request.user.last_name[:1]).upper() if request.user.first_name and request.user.last_name else request.user.email[:2].upper(),
    }
    return render(request, "borrow/my_loans.html", context)


@login_required(login_url='/login/')
def borrow_book(request, book_id):
    """Emprunter un livre."""
    from services.livres.models import Book

    book = get_object_or_404(Book, id=book_id)

    if book.available_copies <= 0:
        messages.error(request, "Ce livre n'est pas disponible actuellement.")
        return redirect('book_detail', book_id=book_id)

    existing_loan = Loan.objects.filter(
        user=request.user,
        book=book,
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]
    ).exists()

    if existing_loan:
        messages.warning(request, "Vous avez déjà emprunté ce livre.")
        return redirect('book_detail', book_id=book_id)

    active_loans_count = Loan.objects.filter(
        user=request.user,
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED]
    ).count()

    from django.conf import settings
    max_loans = {
        "student": 3,
        "teacher": 5,
        "admin": 10,
        "staff": 10,
    }.get(request.user.role, getattr(settings, "MAX_ACTIVE_LOANS", 5))

    if active_loans_count >= max_loans:
        messages.error(request, f"Vous avez atteint la limite d'emprunts ({max_loans} livres maximum).")
        return redirect('book_detail', book_id=book_id)

    due_date = timezone.now().date() + timezone.timedelta(days=14)
    loan = Loan.objects.create(
        user=request.user,
        book=book,
        due_date=due_date,
        status=Loan.Status.ACTIVE
    )

    book.available_copies -= 1
    book.save()

    messages.success(request, f"Vous avez emprunté '{book.title}'. Date de retour: {due_date.strftime('%d/%m/%Y')}.")
    return redirect('my_loans')


@login_required(login_url='/login/')
def return_book(request, loan_id):
    """Retourner un livre."""
    loan = get_object_or_404(Loan, id=loan_id, user=request.user)

    if loan.status not in [Loan.Status.ACTIVE, Loan.Status.RENEWED]:
        messages.error(request, "Cet emprunt n'est pas actif.")
        return redirect('my_loans')

    loan.mark_returned()

    messages.success(request, f"Vous avez retourné '{loan.book.title}'.")
    return redirect('my_loans')


@login_required(login_url='/login/')
def renew_loan(request, loan_id):
    """Renouveler un emprunt."""
    loan = get_object_or_404(Loan, id=loan_id, user=request.user)

    if loan.status not in [Loan.Status.ACTIVE, Loan.Status.RENEWED]:
        messages.error(request, "Cet emprunt ne peut pas être renouvelé.")
        return redirect('my_loans')

    if loan.renewal_count >= 2:
        messages.error(request, "Cet emprunt a déjà été renouvelé 2 fois.")
        return redirect('my_loans')

    if loan.due_date < timezone.now().date():
        messages.error(request, "Les emprunts en retard ne peuvent pas être renouvelés.")
        return redirect('my_loans')

    loan.due_date = loan.due_date + timezone.timedelta(days=14)
    loan.renewal_count += 1
    loan.status = Loan.Status.RENEWED
    loan.save()

    messages.success(request, f"Emprunt renouvelé jusqu'au {loan.due_date.strftime('%d/%m/%Y')}.")
    return redirect('my_loans')
