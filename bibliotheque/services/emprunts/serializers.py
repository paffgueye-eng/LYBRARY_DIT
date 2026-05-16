from rest_framework import serializers
from django.utils import timezone
from .models import Loan, Reservation
from services.livres.serializers import BookListSerializer
from services.utilisateurs.serializers import UserDetailSerializer


class LoanListSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)
    user = UserDetailSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'user', 'book', 'borrowed_at', 'due_date', 'returned_at',
            'status', 'renewal_count', 'is_overdue', 'days_remaining', 'created_at'
        ]
        read_only_fields = ['id', 'borrowed_at', 'returned_at', 'created_at']


class LoanDetailSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)
    user = UserDetailSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'user', 'book', 'borrowed_at', 'due_date', 'returned_at',
            'status', 'renewal_count', 'notes', 'is_overdue', 'days_remaining',
            'days_overdue', 'created_at'
        ]
        read_only_fields = ['id', 'borrowed_at', 'returned_at', 'created_at']


class LoanCreateSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Loan
        fields = ['id', 'book_id', 'borrowed_at', 'due_date', 'status']
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        from services.livres.models import Book
        book_id = validated_data.pop('book_id')
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise serializers.ValidationError({'book_id': 'Ce livre n\'existe pas.'})

        if not book.is_available:
            raise serializers.ValidationError({'book': 'Aucun exemplaire disponible.'})

        validated_data['user'] = self.context['request'].user
        validated_data['book'] = book
        loan = Loan.objects.create(**validated_data)
        book.decrement_copies()
        return loan


class ReservationSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)
    book_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'book', 'book_id', 'reserved_at', 'status', 'expires_at']
        read_only_fields = ['id', 'reserved_at', 'status', 'expires_at']
