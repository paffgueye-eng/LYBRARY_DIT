"""Shared helpers for template views."""


def user_context(user):
    return {
        "user_initials": user.initials,
        "user_full_name": user.full_name or user.email,
        "user_name": user.first_name or user.email.split("@")[0],
        "user_email": user.email,
        "user_role": user.get_role_display(),
        "user_department": user.department or "",
        "user_phone": user.phone or "",
        "user_avatar_url": user.avatar.url if user.avatar else "",
    }
