"""
Moteur de recommandation :
- priorité : microservice FastAPI (TF-IDF + cosinus)
- fallback : règles métier Django (catégories, popularité, favoris)
"""
from collections import defaultdict

from django.db.models import Count, Q

from services.livres.models import Book, Favorite
from services.emprunts.models import Loan

from .ml_client import fetch_recommendations


def get_user_recommendations(user, limit=12):
    """Return list of (book, score, reason) tuples."""
    if not user or not user.is_authenticated:
        return _popular_books_scored(limit)

    ml_items = fetch_recommendations(user.id, limit=limit)
    if ml_items:
        return _from_ml_payload(ml_items, user, limit)

    return _heuristic_recommendations(user, limit)


def _from_ml_payload(items, user, limit):
    ids = [item["id"] for item in items]
    books = {b.id: b for b in Book.objects.filter(id__in=ids).select_related("category")}
    result = []
    for item in items[:limit]:
        book = books.get(item["id"])
        if not book:
            continue
        score = int(round(float(item.get("score", 0.5)) * 100))
        reason = "Recommandé par l'IA (profil de lecture)"
        if item.get("category"):
            reason = f"IA — {item['category']}"
        result.append((book, score, reason))
    if result:
        return result
    return _heuristic_recommendations(user, limit)


def _heuristic_recommendations(user, limit):
    borrowed_ids = set(
        Loan.objects.filter(user=user).values_list("book_id", flat=True)
    )
    active_ids = set(
        Loan.objects.filter(
            user=user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED],
        ).values_list("book_id", flat=True)
    )
    favorite_ids = set(
        Favorite.objects.filter(user=user).values_list("book_id", flat=True)
    )
    exclude_ids = borrowed_ids | active_ids

    category_scores = defaultdict(float)
    loans = Loan.objects.filter(user=user).select_related("book__category")
    for loan in loans:
        if loan.book.category_id:
            weight = 2.0 if loan.status == Loan.Status.RETURNED else 1.5
            category_scores[loan.book.category_id] += weight

    fav_books = Favorite.objects.filter(user=user).select_related("book__category")
    for fav in fav_books:
        if fav.book.category_id:
            category_scores[fav.book.category_id] += 1.0

    popular = (
        Book.objects.filter(available_copies__gt=0)
        .exclude(id__in=exclude_ids)
        .annotate(loan_count=Count("loans"))
        .order_by("-loan_count", "-available_copies")
    )

    scored = []
    for book in popular[: limit * 3]:
        score = 0.0
        reasons = []

        if book.category_id and book.category_id in category_scores:
            cat_score = category_scores[book.category_id]
            score += cat_score * 10
            reasons.append(f"Catégorie « {book.category.name} » que vous appréciez")

        loan_count = getattr(book, "loan_count", 0) or 0
        if loan_count > 0:
            score += min(loan_count * 2, 20)
            reasons.append("Populaire à la bibliothèque")

        if book.id in favorite_ids:
            score += 15
            reasons.append("Dans vos favoris")

        if book.available_copies > 0:
            score += 5

        if score > 0:
            reason = reasons[0] if reasons else "Recommandé pour vous"
            scored.append((book, round(min(score, 100)), reason))

    scored.sort(key=lambda x: x[1], reverse=True)

    if len(scored) < limit:
        for book, score, reason in _popular_books_scored(limit - len(scored)):
            if book.id not in exclude_ids:
                scored.append((book, score, reason))

    return scored[:limit]


def _popular_books_scored(limit):
    books = (
        Book.objects.filter(available_copies__gt=0)
        .annotate(loan_count=Count("loans"))
        .order_by("-loan_count")[:limit]
    )
    return [(b, 60, "Tendance du moment") for b in books]


def get_similar_books(book, limit=4):
    """Books similar by category and author (fallback local)."""
    if not book:
        return Book.objects.none()

    qs = Book.objects.filter(available_copies__gt=0).exclude(pk=book.pk)
    similar = qs.filter(
        Q(category=book.category) | Q(author__icontains=book.author.split(",")[0][:30])
    ).distinct()[:limit]

    if similar.count() < limit:
        extra = qs.exclude(pk__in=similar.values_list("pk", flat=True))[: limit - similar.count()]
        return list(similar) + list(extra)
    return similar
