from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import BookViewSet, LoanViewSet, LoginView, RegisterView, ReservationViewSet, admin_stats, me

router = DefaultRouter(trailing_slash=False)
router.register('books', BookViewSet, basename='book')
router.register('loans', LoanViewSet, basename='loan')
router.register('reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('auth/register', RegisterView.as_view()),
    path('auth/login', LoginView.as_view()),
    path('auth/refresh', TokenRefreshView.as_view()),
    path('users/me', me),
    path('admin/stats', admin_stats),
    path('', include(router.urls)),
]
