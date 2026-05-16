from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """Restrict view access to users with one of the given roles."""
    def decorator(view_func):
        @login_required(login_url="/login/")
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles and not (
                "admin" in roles and request.user.is_admin
            ):
                messages.error(request, "Accès non autorisé pour votre rôle.")
                return redirect("user_home")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


admin_required = role_required("admin", "staff")
teacher_required = role_required("teacher", "admin", "staff")
