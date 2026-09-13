from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from .models import AuditLog, Book, Loan, Reservation, User
from .permissions import IsAdmin
from .serializers import BookSerializer, LoginSerializer, LoanSerializer, RegisterSerializer, ReservationSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


@api_view(['GET'])
def me(request):
    return Response(UserSerializer(request.user).data)


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['title', 'created_at', 'year']
    ordering = ['title']

    def get_queryset(self):
        queryset = Book.objects.select_related('category').prefetch_related('authors')
        params = self.request.query_params
        if search := params.get('search'):
            queryset = queryset.filter(Q(title__icontains=search) | Q(isbn__icontains=search) | Q(summary__icontains=search))
        if category := params.get('category'):
            queryset = queryset.filter(Q(category_id=category) | Q(category__name__icontains=category))
        if author := params.get('author'):
            queryset = queryset.filter(authors__name__icontains=author)
        return queryset.distinct()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoanSerializer
    queryset = Loan.objects.select_related('user', 'book').all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role != User.Role.ADMIN:
            queryset = queryset.filter(user=self.request.user)
        elif user_id := self.request.query_params.get('user_id'):
            queryset = queryset.filter(user_id=user_id)
        if loan_status := self.request.query_params.get('status'):
            queryset = queryset.filter(status=loan_status)
        return queryset

    def create(self, request, *args, **kwargs):
        return self.borrow(request)

    @action(detail=False, methods=['get'], url_path='my')
    def my_loans(self, request):
        return Response(self.get_serializer(self.get_queryset().filter(user=request.user), many=True).data)

    @action(detail=False, methods=['post'], url_path='borrow')
    def borrow(self, request):
        book_id = request.data.get('book_id') or request.data.get('bookId')
        if not book_id:
            return Response({'message': 'book_id 是必填项。'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            book = Book.objects.select_for_update().filter(id=book_id).first()
            if not book:
                return Response({'message': '书目不存在。'}, status=status.HTTP_404_NOT_FOUND)
            if book.available_copies < 1:
                return Response({'message': '当前无可借副本，请先预约。'}, status=status.HTTP_409_CONFLICT)
            active = Loan.objects.filter(user=request.user, book=book, status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE]).exists()
            if active:
                return Response({'message': '你已经借阅了这本书。'}, status=status.HTTP_409_CONFLICT)
            loan = Loan.objects.create(user=request.user, book=book, due_at=timezone.now() + timedelta(days=30))
            book.available_copies -= 1
            book.save(update_fields=['available_copies', 'updated_at'])
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'patch'], url_path='return')
    def return_loan(self, request, pk=None):
        with transaction.atomic():
            loan = Loan.objects.select_for_update().select_related('book').filter(id=pk).first()
            if not loan:
                return Response({'message': '借阅记录不存在。'}, status=status.HTTP_404_NOT_FOUND)
            if request.user.role != User.Role.ADMIN and loan.user_id != request.user.id:
                return Response({'message': '无权操作此借阅记录。'}, status=status.HTTP_403_FORBIDDEN)
            if loan.returned_at:
                return Response(LoanSerializer(loan).data)
            now = timezone.now()
            overdue_days = max((now.date() - loan.due_at.date()).days, 0)
            loan.returned_at = now
            loan.status = Loan.Status.RETURNED
            loan.fine_amount = Decimal(overdue_days) * settings.FINE_PER_DAY
            loan.save(update_fields=['returned_at', 'status', 'fine_amount'])
            Book.objects.filter(id=loan.book_id).update(available_copies=F('available_copies') + 1, updated_at=now)
        return Response(LoanSerializer(loan).data)


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = Reservation.objects.select_related('book', 'user')
        if self.request.user.role != User.Role.ADMIN:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        if book.available_copies > 0:
            raise serializers.ValidationError('当前有可借副本，无需预约。')
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            raise serializers.ValidationError('你已经预约了这本书。')


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_stats(request):
    now = timezone.now()
    overdue = Loan.objects.filter(status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE], due_at__lt=now).count()
    active = Loan.objects.filter(status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE]).count()
    popular = list(Book.objects.annotate(borrow_count=Count('loans')).order_by('-borrow_count', 'title').values('id', 'title', 'borrow_count')[:10])
    total_copies = Book.objects.aggregate(total=Sum('total_copies'))['total'] or 0
    available_copies = Book.objects.aggregate(total=Sum('available_copies'))['total'] or 0
    return Response({'total_books': Book.objects.count(), 'totalBooks': Book.objects.count(), 'total_copies': total_copies, 'totalCopies': total_copies, 'available_copies': available_copies, 'availableCopies': available_copies, 'active_loans': active, 'activeLoans': active, 'overdue_loans': overdue, 'overdueLoans': overdue, 'popular_books': popular})
