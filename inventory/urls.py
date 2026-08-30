from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    # Web views
    login_view,
    logout_view,
    dashboard_view,
    product_list_view,
    product_create_view,
    product_update_view,
    product_delete_view,
    product_detail_view,
    category_list_view,
    category_create_view,
    category_update_view,
    category_delete_view,
    transaction_list_view,
    transaction_create_view,
    user_list_view,
    user_create_view,
    user_update_view,
    user_toggle_status_view,
    profile_view,
    # DRF API ViewSets
    CustomTokenObtainPairView,
    UserViewSet,
    CategoryViewSet,
    ProductViewSet,
    StockTransactionViewSet,
)

# Router para REST API
api_router = DefaultRouter()
api_router.register(r'users', UserViewSet, basename='api-user')
api_router.register(r'categories', CategoryViewSet, basename='api-category')
api_router.register(r'products', ProductViewSet, basename='api-product')
api_router.register(r'transactions', StockTransactionViewSet, basename='api-transaction')

urlpatterns = [
    # -------------------------------------------------------------
    # Interfaz Web Monolítica
    # -------------------------------------------------------------
    path('', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),

    # Productos
    path('products/', product_list_view, name='product_list'),
    path('products/new/', product_create_view, name='product_create'),
    path('products/<int:pk>/', product_detail_view, name='product_detail'),
    path('products/<int:pk>/edit/', product_update_view, name='product_update'),
    path('products/<int:pk>/delete/', product_delete_view, name='product_delete'),

    # Categorías
    path('categories/', category_list_view, name='category_list'),
    path('categories/new/', category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', category_update_view, name='category_update'),
    path('categories/<int:pk>/delete/', category_delete_view, name='category_delete'),

    # Movimientos / Transacciones
    path('transactions/', transaction_list_view, name='transaction_list'),
    path('transactions/new/', transaction_create_view, name='transaction_create'),

    # Usuarios (Solo Admin)
    path('users/', user_list_view, name='user_list'),
    path('users/new/', user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', user_update_view, name='user_update'),
    path('users/<int:pk>/toggle/', user_toggle_status_view, name='user_toggle_status'),

    # -------------------------------------------------------------
    # Endpoints REST API (SimpleJWT + ViewSets)
    # -------------------------------------------------------------
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(api_router.urls)),
]