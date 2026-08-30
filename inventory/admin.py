from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Category, Product, StockTransaction


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol (RBAC)', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Rol (RBAC)', {'fields': ('role',)}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    search_fields = ['name', 'description']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'price', 'stock_actual', 'created_at', 'updated_at']
    list_filter = ['category', 'created_at']
    search_fields = ['sku', 'name', 'description']
    readonly_fields = ['stock_actual', 'created_at', 'updated_at']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'transaction_type', 'product', 'quantity', 'user', 'notes']
    list_filter = ['transaction_type', 'created_at', 'user']
    search_fields = ['product__name', 'product__sku', 'notes', 'user__username']
    readonly_fields = ['created_at']
