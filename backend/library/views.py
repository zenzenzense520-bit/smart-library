from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from .models import AuditLog, Book, Loan, Notification, Reservation, User
from .permissions import IsAdmin
from .recommendation import RecommendationEngine
from .serializers import (
    BookSerializer,
    LoginSerializer,
    LoanSerializer,
    NotificationSerializer,
    RegisterSerializer,
    ReservationSerializer,
    UserSerializer,
)
from .services import NotificationService, ReservationService


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

        loan, error_msg, err_status = ReservationService.claim_or_borrow(request.user, book_id)
        if error_msg:
            return Response({'message': error_msg}, status=err_status)

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

            # 归还后自动触发预约排队队列顺延与通知
            ReservationService.on_book_returned(loan.book)

        return Response(LoanSerializer(loan).data)


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        # 懒惰触发超时检测，保证每次查询前状态最新
        ReservationService.check_and_release_expired_reservations()

        queryset = Reservation.objects.select_related('book__category', 'user').prefetch_related('book__authors')
        if self.request.user.role != User.Role.ADMIN:
            queryset = queryset.filter(user=self.request.user)
        if book_id := self.request.query_params.get('book_id'):
            queryset = queryset.filter(book_id=book_id)
        if res_status := self.request.query_params.get('status'):
            queryset = queryset.filter(status=res_status)
        return queryset

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        ReservationService.check_and_release_expired_reservations(book.id)

        # 检查是否已有可借副本
        if book.available_copies > 0:
            raise serializers.ValidationError('当前有可借副本，无需预约。')

        # 检查用户是否已有借阅中记录
        active_loan = Loan.objects.filter(
            user=self.request.user,
            book=book,
            status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE]
        ).exists()
        if active_loan:
            raise serializers.ValidationError('你已经借阅了这本书。')

        # 检查用户是否已有待满足的有效预约
        existing = Reservation.objects.filter(
            user=self.request.user,
            book=book,
            status__in=[Reservation.Status.WAITING, Reservation.Status.NOTIFIED]
        ).exists()
        if existing:
            raise serializers.ValidationError('你已经预约了这本书。')

        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            raise serializers.ValidationError('你已经预约了这本书。')

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        res, error_msg = ReservationService.cancel_reservation(request.user, pk)
        if error_msg:
            return Response({'message': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReservationSerializer(res).data)

    @action(detail=True, methods=['post'], url_path='claim')
    def claim(self, request, pk=None):
        res = self.get_queryset().filter(id=pk).first()
        if not res:
            return Response({'message': '预约记录不存在。'}, status=status.HTTP_404_NOT_FOUND)
        if res.status != Reservation.Status.NOTIFIED:
            return Response({'message': '该预约暂未到馆或已被取消，无法借阅。'}, status=status.HTTP_400_BAD_REQUEST)

        loan, error_msg, err_status = ReservationService.claim_or_borrow(request.user, res.book_id)
        if error_msg:
            return Response({'message': error_msg}, status=err_status)
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('related_book')

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count, 'unreadCount': count})

    @action(detail=True, methods=['post', 'patch'], url_path='read')
    def mark_read(self, request, pk=None):
        notif = self.get_queryset().filter(id=pk).first()
        if not notif:
            return Response({'message': '通知不存在。'}, status=status.HTTP_404_NOT_FOUND)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': '所有通知已标记为已读。'})


@api_view(['GET'])
def recommendations_for_you(request):
    limit = int(request.query_params.get('limit', 6))
    data = RecommendationEngine.get_recommendations_for_user(request.user, limit=limit)
    return Response(data)


@api_view(['GET'])
def related_books(request, pk):
    limit = int(request.query_params.get('limit', 4))
    book = get_object_or_404(Book, id=pk)
    data = RecommendationEngine.get_related_books(book, limit=limit)
    return Response(data)


@api_view(['GET'])
def user_reading_profile(request):
    data = RecommendationEngine.get_user_profile(request.user)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_stats(request):
    now = timezone.now()
    ReservationService.check_and_release_expired_reservations()

    overdue = Loan.objects.filter(status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE], due_at__lt=now).count()
    active = Loan.objects.filter(status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE]).count()
    popular = list(Book.objects.annotate(borrow_count=Count('loans')).order_by('-borrow_count', 'title').values('id', 'title', 'borrow_count')[:10])
    total_copies = Book.objects.aggregate(total=Sum('total_copies'))['total'] or 0
    available_copies = Book.objects.aggregate(total=Sum('available_copies'))['total'] or 0
    waiting_reservations = Reservation.objects.filter(status=Reservation.Status.WAITING).count()
    notified_reservations = Reservation.objects.filter(status=Reservation.Status.NOTIFIED).count()

    return Response({
        'total_books': Book.objects.count(),
        'totalBooks': Book.objects.count(),
        'total_copies': total_copies,
        'totalCopies': total_copies,
        'available_copies': available_copies,
        'availableCopies': available_copies,
        'active_loans': active,
        'activeLoans': active,
        'overdue_loans': overdue,
        'overdueLoans': overdue,
        'popular_books': popular,
        'waiting_reservations': waiting_reservations,
        'waitingReservations': waiting_reservations,
        'notified_reservations': notified_reservations,
        'notifiedReservations': notified_reservations,
    })
