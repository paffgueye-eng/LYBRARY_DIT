from django.urls import path
from . import views

urlpatterns = [
    path("", views.notifications_page, name="notifications_page"),
    path("read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
]
