from django.urls import path
from .views import book_list, book_detail, toggle_favorite, reserve_book

urlpatterns = [
    path("", book_list, name="book_list"),
    path("<int:book_id>/", book_detail, name="book_detail"),
    path("<int:book_id>/favorite/", toggle_favorite, name="toggle_favorite"),
    path("<int:book_id>/reserve/", reserve_book, name="reserve_book"),
]
