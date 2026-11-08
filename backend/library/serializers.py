from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Author, Book, Category, Loan, Notification, Reservation, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'created_at']
        read_only_fields = ['id', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=[User.Role.STUDENT, User.Role.STAFF, User.Role.ADMIN, 'teacher'])

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'role']

    def validate_role(self, value):
        return User.Role.STAFF if value == 'teacher' else value

    def create(self, validated_data):
        if validated_data.get('role') == User.Role.ADMIN and not self.context['request'].user.is_staff:
            validated_data['role'] = User.Role.STUDENT
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('邮箱或密码错误。')
        refresh = RefreshToken.for_user(user)
        return {'token': str(refresh.access_token), 'refresh': str(refresh), 'user': UserSerializer(user).data}


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    author = serializers.SerializerMethodField()
    author_ids = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), many=True, write_only=True, required=False, source='authors')
    category_name = serializers.CharField(source='category.name', read_only=True)
    description = serializers.CharField(source='summary', read_only=True)
    totalCopies = serializers.IntegerField(source='total_copies', read_only=True)
    availableCopies = serializers.IntegerField(source='available_copies', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'isbn', 'publisher', 'year', 'summary', 'description',
            'category', 'category_name', 'authors', 'author', 'author_ids',
            'total_copies', 'available_copies', 'totalCopies', 'availableCopies',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'available_copies', 'created_at', 'updated_at']

    def get_author(self, obj):
        return ', '.join(a.name for a in obj.authors.all()) or '未知作者'

    def create(self, validated_data):
        authors = validated_data.pop('authors', [])
        book = Book.objects.create(available_copies=validated_data['total_copies'], **validated_data)
        book.authors.set(authors)
        return book

    def update(self, instance, validated_data):
        authors = validated_data.pop('authors', None)
        total_copies = validated_data.get('total_copies')
        if total_copies is not None:
            borrowed = instance.total_copies - instance.available_copies
            if total_copies < borrowed:
                raise serializers.ValidationError({'total_copies': '馆藏总数不能少于当前借出数量。'})
            validated_data['available_copies'] = total_copies - borrowed
        book = super().update(instance, validated_data)
        if authors is not None:
            book.authors.set(authors)
        return book


class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.name', read_only=True)
    dueDate = serializers.DateTimeField(source='due_at', read_only=True)
    returnedAt = serializers.DateTimeField(source='returned_at', read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'user', 'user_name', 'book', 'book_title', 'book_author',
            'borrowed_at', 'due_at', 'dueDate', 'returned_at', 'returnedAt',
            'status', 'fine_amount'
        ]
        read_only_fields = fields

    def get_book_author(self, obj):
        return ', '.join(a.name for a in obj.book.authors.all()) or '未知作者'


class ReservationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.SerializerMethodField()
    book_category = serializers.CharField(source='book.category.name', read_only=True, default='')
    book_available_copies = serializers.IntegerField(source='book.available_copies', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    queue_position = serializers.SerializerMethodField()
    remaining_seconds = serializers.SerializerMethodField()
    hold_expires_at = serializers.DateTimeField(read_only=True)
    notified_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'user', 'user_name', 'book', 'book_title', 'book_author',
            'book_category', 'book_available_copies', 'reserved_at', 'notified_at',
            'hold_expires_at', 'status', 'queue_position', 'remaining_seconds'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'reserved_at', 'notified_at', 'hold_expires_at', 'status']

    def get_book_author(self, obj):
        return ', '.join(a.name for a in obj.book.authors.all()) or '未知作者'

    def get_queue_position(self, obj):
        if obj.status == Reservation.Status.NOTIFIED:
            return 0
        if obj.status == Reservation.Status.WAITING:
            ahead = Reservation.objects.filter(
                book=obj.book,
                status=Reservation.Status.WAITING,
                reserved_at__lt=obj.reserved_at
            ).count()
            return ahead + 1
        return None

    def get_remaining_seconds(self, obj):
        if obj.status == Reservation.Status.NOTIFIED and obj.hold_expires_at:
            diff = (obj.hold_expires_at - timezone.now()).total_seconds()
            return max(0, int(diff))
        return None


class NotificationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='related_book.title', read_only=True, default='')
    created_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'content', 'notification_type', 'is_read',
            'created_at', 'created_at_display', 'related_book', 'book_title'
        ]
        read_only_fields = [
            'id', 'title', 'content', 'notification_type', 'created_at',
            'created_at_display', 'related_book', 'book_title'
        ]

    def get_created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
