from django.urls import path
from .views import platform_analytics

urlpatterns = [
    path("platform/", platform_analytics, name="platform_analytics"),
]
