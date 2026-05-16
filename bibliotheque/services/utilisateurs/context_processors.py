"""Contexte global — allégé sur les pages auth publiques."""

# Préfixe de chemins sans requêtes SQL (login, logout)
AUTH_LIGHT_PREFIXES = ("/login", "/logout")


def library_user(request):
    path = request.path
    if path.startswith(AUTH_LIGHT_PREFIXES):
        return {}

    ctx = {
        "user_initials": "U",
        "user_full_name": "Utilisateur",
        "user_email": "",
        "user_role": "",
        "user_department": "",
        "user_avatar_url": "",
        "user_is_staff": False,
        "unread_notifications_count": 0,
        "active_loans_count": 0,
    }
    if not request.user.is_authenticated:
        return ctx

    user = request.user
    ctx.update({
        "user_initials": user.initials,
        "user_full_name": user.full_name or user.email,
        "user_email": user.email,
        "user_role": user.get_role_display(),
        "user_department": user.department or "",
        "user_avatar_url": user.avatar.url if user.avatar else "",
        "user_is_staff": user.is_staff or getattr(user, "is_admin", False),
    })
    try:
        from services.emprunts.models import Loan
        from services.notifications.models import Notification

        ctx["unread_notifications_count"] = Notification.objects.filter(
            user=user, is_read=False
        ).count()
        ctx["active_loans_count"] = Loan.objects.filter(
            user=user,
            status__in=[Loan.Status.ACTIVE, Loan.Status.RENEWED],
        ).count()
    except Exception:
        pass

    if getattr(user, "is_admin", False) or user.is_staff:
        try:
            from services.analytics.services import get_platform_stats
            ctx["stats"] = get_platform_stats()
        except Exception:
            ctx["stats"] = {}
    return ctx
