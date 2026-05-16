from django.contrib import admin
from .models import Book, Category, BookReview, Favorite


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "isbn", "category", "available_copies", "total_copies", "year"]
    list_filter = ["category", "language", "year"]
    search_fields = ["title", "author", "isbn", "keywords"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Informations bibliographiques", {
            "fields": ("title", "author", "isbn", "publisher", "year", "pages", "language", "description", "cover"),
        }),
        ("Classification", {"fields": ("category", "keywords")}),
        ("Inventaire & Localisation", {
            "fields": ("total_copies", "available_copies", "location", "call_number"),
        }),
        ("Metadonnees", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(BookReview)
class BookReviewAdmin(admin.ModelAdmin):
    list_display = ["book", "user", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["book__title", "user__email"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "created_at"]
    search_fields = ["user__email", "book__title"]
