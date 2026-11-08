from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BookViewSet,
    LoanViewSet,
    LoginView,
    NotificationViewSet,
    RegisterView,
    ReservationViewSet,
    admin_stats,
    me,
    recommendations_for_you,
    related_books,
    user_reading_profile,
)

router = DefaultRouter(trailing_slash=False)
router.register('books', BookViewSet, basename='book')
router.register('loans', LoanViewSet, basename='loan')
router.register('reservations', ReservationViewSet, basename='reservation')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/register', RegisterView.as_view()),
    path('auth/login', LoginView.as_view()),
    path('auth/refresh', TokenRefreshView.as_view()),
    path('users/me', me),
    path('admin/stats', admin_stats),
    path('recommendations/for-you', recommendations_for_you),
    path('recommendations/books/<uuid:pk>/related', related_books),
    path('recommendations/user-profile', user_reading_profile),
    path('', include(router.urls)),
]
