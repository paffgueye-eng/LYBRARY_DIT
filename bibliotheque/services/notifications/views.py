from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"detail": "Toutes les notifications ont été lues."})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


@login_required(login_url="/login/")
def notifications_page(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    unread_count = qs.filter(is_read=False).count()
    notifications = list(qs[:50])
    return render(request, "notifications/list.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })


@login_required(login_url="/login/")
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications_page")


@login_required(login_url="/login/")
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.link:
        link = notification.link.strip()
        if link.startswith("/"):
            return redirect(link)
        return redirect(notification.link)
    return redirect("notifications_page")
