from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = '仅管理员可以执行此操作。'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
