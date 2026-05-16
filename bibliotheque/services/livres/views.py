from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from services.utilisateurs.permissions import IsAdminUser
from .models import Book, Category, Favorite
from services.recommandation.services import get_similar_books
from services.utilisateurs.utils import user_context
from .serializers import (
    BookListSerializer, BookDetailSerializer,
    CategorySerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission pour que les admins aient accès complet, les autres en lecture seule."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


@extend_schema_view(
    list=extend_schema(tags=["books"], summary="Lister les livres"),
    retrieve=extend_schema(tags=["books"], summary="Détail d'un livre"),
    create=extend_schema(tags=["books"], summary="Ajouter un livre"),
    update=extend_schema(tags=["books"], summary="Modifier un livre"),
    partial_update=extend_schema(tags=["books"], summary="Modifier partiellement"),
    destroy=extend_schema(tags=["books"], summary="Supprimer un livre"),
)
class BookViewSet(viewsets.ModelViewSet):
    """
    CRUD complet sur le catalogue.
    - List / Retrieve → tous les utilisateurs authentifiés
    - Create / Update / Delete → admin seulement
    """
    queryset = Book.objects.select_related("category").all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author", "isbn", "keywords", "publisher"]
    ordering_fields = ["title", "author", "year", "created_at", "available_copies"]
    ordering = ["title"]

    def get_serializer_class(self):
        if self.action in ("list",):
            return BookListSerializer
        return BookDetailSerializer

    @extend_schema(tags=["books"], summary="Livres disponibles seulement")
    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request):
        qs = self.get_queryset().filter(available_copies__gt=0)
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(BookListSerializer(page, many=True).data)
        return Response(BookListSerializer(qs, many=True).data)


@extend_schema_view(
    list=extend_schema(tags=["books"], summary="Lister les catégories"),
    retrieve=extend_schema(tags=["books"], summary="Détail d'une catégorie"),
    create=extend_schema(tags=["books"], summary="Créer une catégorie"),
    update=extend_schema(tags=["books"], summary="Modifier une catégorie"),
    destroy=extend_schema(tags=["books"], summary="Supprimer une catégorie"),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name"]


@login_required(login_url="/login/")
def book_list(request):
    """Catalogue avec recherche, filtres et pagination."""
    books = Book.objects.select_related("category").all()

    search_query = request.GET.get("search", "").strip()
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query)
            | Q(author__icontains=search_query)
            | Q(isbn__icontains=search_query)
            | Q(keywords__icontains=search_query)
        )

    category_id = request.GET.get("category")
    if category_id:
        books = books.filter(category_id=category_id)

    availability = request.GET.get("availability")
    if availability == "available":
        books = books.filter(available_copies__gt=0)

    paginator = Paginator(books.order_by("title"), 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        **user_context(request.user),
        "books": page_obj,
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "search_query": search_query,
        "selected_category": category_id,
        "filter_availability": availability,
    }
    return render(request, "books/catalog.html", context)


@login_required(login_url="/login/")
def book_detail(request, book_id):
    book = get_object_or_404(Book.objects.select_related("category"), id=book_id)
    from services.emprunts.models import Loan, Reservation

    has_active_loan = Loan.objects.filter(
        user=request.user,
        book=book,
        status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED],
    ).exists()
    is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()
    similar_books = get_similar_books(book, limit=4)

    context = {
        **user_context(request.user),
        "book": book,
        "can_borrow": book.available_copies > 0 and not has_active_loan,
        "has_active_loan": has_active_loan,
        "is_favorite": is_favorite,
        "similar_books": similar_books,
        "can_reserve": book.available_copies <= 0 and not Reservation.objects.filter(
            user=request.user, book=book, status=Reservation.Status.PENDING
        ).exists(),
    }
    return render(request, "books/detail.html", context)


@login_required(login_url="/login/")
def toggle_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if not created:
        fav.delete()
        messages.info(request, f"« {book.title} » retiré des favoris.")
    else:
        messages.success(request, f"« {book.title} » ajouté aux favoris.")
    return redirect("book_detail", book_id=book_id)


@login_required(login_url="/login/")
def reserve_book(request, book_id):
    from services.emprunts.models import Reservation
    from services.notifications.models import Notification
    from services.notifications.services import notify

    book = get_object_or_404(Book, id=book_id)
    if book.available_copies > 0:
        messages.warning(request, "Ce livre est disponible — empruntez-le directement.")
        return redirect("book_detail", book_id=book_id)

    _, created = Reservation.objects.get_or_create(
        user=request.user,
        book=book,
        status=Reservation.Status.PENDING,
    )
    if created:
        notify(
            request.user,
            Notification.Type.RESERVATION,
            f"Réservation : {book.title}",
            "Vous serez notifié dès qu'un exemplaire sera disponible.",
            link=f"/books/{book.id}/",
        )
        messages.success(request, "Réservation enregistrée.")
    else:
        messages.info(request, "Vous avez déjà réservé ce livre.")
    return redirect("book_detail", book_id=book_id)
