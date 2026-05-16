from django.contrib import admin
from django.utils.html import format_html
from .models import Loan, Reservation


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "borrowed_at", "due_date", "returned_at", "status_badge", "days_overdue"]
    list_filter = ["status"]
    search_fields = ["user__email", "user__last_name", "book__title", "book__isbn"]
    readonly_fields = ["created_at"]
    date_hierarchy = "borrowed_at"
    ordering = ["-borrowed_at"]

    def status_badge(self, obj):
        colors = {
            "active": "#43a047",
            "returned": "#1e88e5",
            "overdue": "#e53935",
            "renewed": "#fb8c00",
        }
        color = colors.get(obj.status, "#666")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Statut"

    def days_overdue(self, obj):
        return obj.days_overdue or "—"
    days_overdue.short_description = "Jours de retard"


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "status", "reserved_at", "expires_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "book__title"]
