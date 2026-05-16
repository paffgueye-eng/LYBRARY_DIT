from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "DIT Library — Administration"
admin.site.site_title = "DIT Library Admin"
admin.site.index_title = "Gestion de la bibliothèque"
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from services.utilisateurs.views_web import (
    index_page,
    login_page,
    user_home,
    profile_page,
    logout_view,
)
from services.utilisateurs.admin_views import (
    admin_dashboard, admin_loans, admin_users,
    admin_catalog, admin_recommendations, admin_notifications,
)

urlpatterns = [
    path("logout/", logout_view, name="logout"),
    path("", index_page, name="index"),
    path("admin/", admin.site.urls),
    path("login/", login_page, name="login"),
    path("home/", user_home, name="home"),
    path("user-home/", user_home, name="user_home"),
    path("profile/", profile_page, name="profile"),
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/emprunts/", admin_loans, name="admin_loans"),
    path("dashboard/utilisateurs/", admin_users, name="admin_users"),
    path("dashboard/catalogue/", admin_catalog, name="admin_catalog"),
    path("dashboard/recommandations/", admin_recommendations, name="admin_recommendations"),
    path("dashboard/notifications/", admin_notifications, name="admin_notifications"),
    path("books/", include("services.livres.urls")),
    path("loans/", include("services.emprunts.urls")),
    path("recommendations/", include("services.recommandation.urls")),
    path("notifications/", include("services.notifications.urls")),
    path("api/", include([
        path("", include("services.utilisateurs.urls")),
        path("books/", include("services.livres.api_urls")),
        path("loans/", include("services.emprunts.api_urls")),
        path("notifications/", include("services.notifications.api_urls")),
        path("recommendations/", include("services.recommandation.api_urls")),
        path("analytics/", include("services.analytics.api_urls")),
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None)
