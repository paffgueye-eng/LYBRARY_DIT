from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services.utilisateurs.utils import user_context
from .services import get_user_recommendations


@login_required(login_url="/login/")
def recommendations_page(request):
    recommendations = get_user_recommendations(request.user, limit=16)
    return render(request, "recommendation/list.html", {
        **user_context(request.user),
        "recommendations": recommendations,
        "total_recommendations": len(recommendations),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_recommendations(request):
    limit = int(request.query_params.get("limit", 12))
    data = []
    for book, score, reason in get_user_recommendations(request.user, limit=limit):
        data.append({
            "book": {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "cover": book.cover.url if book.cover else None,
                "category": book.category.name if book.category else None,
                "available_copies": book.available_copies,
            },
            "score": score,
            "reason": reason,
        })
    return Response(data)
