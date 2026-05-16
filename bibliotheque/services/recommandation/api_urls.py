from django.urls import path
from .views import api_recommendations

urlpatterns = [
    path("", api_recommendations, name="api_recommendations"),
]
