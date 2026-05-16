from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from services.utilisateurs.permissions import IsAdminUser
from .services import get_platform_stats, get_top_books, get_recent_loans, get_users_by_role


@api_view(["GET"])
@permission_classes([IsAdminUser])
def platform_analytics(request):
    stats = get_platform_stats()
    top_books = [
        {"id": b.id, "title": b.title, "author": b.author, "loans": b.loan_count}
        for b in get_top_books()
    ]
    recent = [
        {
            "id": l.id,
            "user": l.user.full_name,
            "book": l.book.title,
            "status": l.status,
            "borrowed_at": str(l.borrowed_at),
        }
        for l in get_recent_loans()
    ]
    return Response({
        "stats": stats,
        "top_books": top_books,
        "recent_loans": recent,
        "users_by_role": list(get_users_by_role()),
    })
