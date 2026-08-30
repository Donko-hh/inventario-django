from rest_framework import permissions
from .models import CustomUser


def is_admin_user(user):
    return bool(user and user.is_authenticated and (str(user.role).lower() == 'admin' or user.is_superuser))


def is_bodeguero_user(user):
    return bool(user and user.is_authenticated and str(user.role).lower() == 'bodeguero')


def is_operario_user(user):
    return bool(user and user.is_authenticated and str(user.role).lower() == 'operario')


class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsBodegueroUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_bodeguero_user(request.user)


class IsOperarioUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_operario_user(request.user)


class IsAdminOrBodeguero(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user) or is_bodeguero_user(request.user)


class ProductCategoryPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return is_admin_user(request.user) or is_bodeguero_user(request.user)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return is_admin_user(request.user) or is_bodeguero_user(request.user)


class StockTransactionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == 'POST':
            return True

        return is_admin_user(request.user) or is_bodeguero_user(request.user)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return is_admin_user(request.user) or is_bodeguero_user(request.user)
