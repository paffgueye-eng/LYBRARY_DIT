from django.urls import path
from .views import my_loans, borrow_book, return_book, renew_loan

urlpatterns = [
    path('', my_loans, name='my_loans'),
    path('borrow/<int:book_id>/', borrow_book, name='borrow_book'),
    path('return/<int:loan_id>/', return_book, name='return_book'),
    path('renew/<int:loan_id>/', renew_loan, name='renew_loan'),
]
