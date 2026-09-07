from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .decorators import admin_required, bodeguero_or_admin_required, role_required
from .forms import (
    CategoryForm,
    CustomUserCreationForm,
    CustomUserEditForm,
    LoginForm,
    ProductForm,
    StockTransactionForm,
    UserProfileForm,
)
from .models import Category, CustomUser, Product, StockTransaction
from .permissions import (
    IsAdminUserRole,
    ProductCategoryPermission,
    StockTransactionPermission,
)
from .serializers import (
    CategorySerializer,
    CustomTokenObtainPairSerializer,
    CustomUserSerializer,
    ProductSerializer,
    StockTransactionSerializer,
    UserCreateUpdateSerializer,
)


# ==============================================================================
# VISTAS WEB (FRONTEND MONOLÍTICO CON TAILWIND CSS)
# ==============================================================================

def login_view(request):
    "Vista de inicio de sesión web."
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido de nuevo, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    "Cierre de sesión web."
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


@login_required(login_url='login')
def dashboard_view(request):
    "Dashboard principal adaptativo según el perfil del usuario."
    user = request.user
    today = date.today()

    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum('stock_actual'))['total'] or 0
    total_value = Product.objects.annotate(val=F('stock_actual') * F('price')).aggregate(total=Sum('val'))['total'] or Decimal('0.00')
    low_stock_count = Product.objects.filter(stock_actual__lte=5).count()
    out_of_stock_count = Product.objects.filter(stock_actual=0).count()

    total_categories = Category.objects.count()
    total_users = CustomUser.objects.count()
    today_transactions = StockTransaction.objects.filter(created_at__date=today).count()

    recent_transactions = StockTransaction.objects.select_related('product', 'user').all()[:8]
    low_stock_products = Product.objects.filter(stock_actual__lte=5).select_related('category').order_by('stock_actual')[:6]

    # Distribución para gráficos
    categories_distribution = Category.objects.annotate(prod_count=Count('products')).filter(prod_count__gt=0)[:6]
    entradas_count = StockTransaction.objects.filter(transaction_type=StockTransaction.TransactionType.ENTRADA).count()
    salidas_count = StockTransaction.objects.filter(transaction_type=StockTransaction.TransactionType.SALIDA).count()

    # 1. Datos específicos para Administrador
    admin_active_users = CustomUser.objects.filter(is_active=True).count()
    admin_users_by_role = {
        'admins': CustomUser.objects.filter(role='admin').count(),
        'bodegueros': CustomUser.objects.filter(role='bodeguero').count(),
        'operarios': CustomUser.objects.filter(role='operario').count(),
    }
    top_valued_products = Product.objects.annotate(
        total_val=F('stock_actual') * F('price')
    ).select_related('category').order_by('-total_val')[:5]

    # 2. Datos específicos para Jefe de Bodega
    warehouse_restock_list = Product.objects.filter(stock_actual__lte=5).select_related('category').order_by('stock_actual')[:10]
    category_stock_breakdown = Category.objects.annotate(
        prod_count=Count('products'),
        units_sum=Sum('products__stock_actual')
    ).order_by('-units_sum')[:5]
    today_in_units = StockTransaction.objects.filter(created_at__date=today, transaction_type='ENTRADA').aggregate(total=Sum('quantity'))['total'] or 0
    today_out_units = StockTransaction.objects.filter(created_at__date=today, transaction_type='SALIDA').aggregate(total=Sum('quantity'))['total'] or 0

    # 3. Datos específicos para Operario
    my_today_txs = StockTransaction.objects.filter(user=user, created_at__date=today)
    my_today_count = my_today_txs.count()
    my_today_entradas = my_today_txs.filter(transaction_type='ENTRADA').count()
    my_today_salidas = my_today_txs.filter(transaction_type='SALIDA').count()
    my_recent_txs = StockTransaction.objects.filter(user=user).select_related('product')[:8]
    quick_products = Product.objects.all().order_by('name')[:8]

    context = {
        'total_products': total_products,
        'total_stock': total_stock,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_categories': total_categories,
        'total_users': total_users,
        'today_transactions': today_transactions,
        'recent_transactions': recent_transactions,
        'low_stock_products': low_stock_products,
        'categories_distribution': categories_distribution,
        'entradas_count': entradas_count,
        'salidas_count': salidas_count,
        # Admin
        'admin_active_users': admin_active_users,
        'admin_users_by_role': admin_users_by_role,
        'top_valued_products': top_valued_products,
        # Bodeguero
        'warehouse_restock_list': warehouse_restock_list,
        'category_stock_breakdown': category_stock_breakdown,
        'today_in_units': today_in_units,
        'today_out_units': today_out_units,
        # Operario
        'my_today_count': my_today_count,
        'my_today_entradas': my_today_entradas,
        'my_today_salidas': my_today_salidas,
        'my_recent_txs': my_recent_txs,
        'quick_products': quick_products,
    }
    return render(request, 'inventory/dashboard.html', context)


# ------------------------------------------------------------------------------
# GESTIÓN DE PRODUCTOS
# ------------------------------------------------------------------------------

@login_required(login_url='login')
def product_list_view(request):
    "Listado de productos con búsqueda, filtros y badges de stock."
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    stock_status = request.GET.get('stock_status', '')

    products = Product.objects.select_related('category').all().order_by('name')

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if stock_status == 'low':
        products = products.filter(stock_actual__gt=0, stock_actual__lte=5)
    elif stock_status == 'out':
        products = products.filter(stock_actual=0)
    elif stock_status == 'available':
        products = products.filter(stock_actual__gt=5)

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'selected_stock_status': stock_status,
        'total_results': products.count(),
    }
    return render(request, 'inventory/product_list.html', context)


@bodeguero_or_admin_required
def product_create_view(request):
    "Creación de un nuevo producto (Admin y Jefe de Bodega)."
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Producto {product.name} (SKU: {product.sku}) creado exitosamente.')
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Nuevo Producto'})


@bodeguero_or_admin_required
def product_update_view(request, pk):
    "Edición de un producto existente (Admin y Jefe de Bodega)."
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto {product.name} actualizado correctamente.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'inventory/product_form.html', {'form': form, 'product': product, 'title': 'Editar Producto'})


@bodeguero_or_admin_required
def product_delete_view(request, pk):
    "Eliminación de un producto (Admin y Jefe de Bodega)."
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        if product.transactions.exists():
            messages.error(request, f'No se puede eliminar {product.name} porque tiene transacciones registradas.')
            return redirect('product_list')
        name = product.name
        product.delete()
        messages.success(request, f'Producto {name} eliminado.')
        return redirect('product_list')
    return render(request, 'inventory/confirm_delete.html', {'object': product, 'type': 'Producto'})


@login_required(login_url='login')
def product_detail_view(request, pk):
    "Detalle de producto y su historial de movimientos."
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    transactions = product.transactions.select_related('user').all()[:20]
    return render(request, 'inventory/product_detail.html', {'product': product, 'transactions': transactions})


# ------------------------------------------------------------------------------
# GESTIÓN DE CATEGORÍAS
# ------------------------------------------------------------------------------

@login_required(login_url='login')
def category_list_view(request):
    "Listado de categorías con conteo de productos."
    categories = Category.objects.annotate(
        prod_count=Count('products'),
        total_units=Sum('products__stock_actual')
    ).all().order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})


@bodeguero_or_admin_required
def category_create_view(request):
    "Crear categoría (Admin y Jefe de Bodega)."
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Categoría {category.name} creada.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Nueva Categoría'})


@bodeguero_or_admin_required
def category_update_view(request, pk):
    "Editar categoría (Admin y Jefe de Bodega)."
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría {category.name} actualizada.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'category': category, 'title': 'Editar Categoría'})


@bodeguero_or_admin_required
def category_delete_view(request, pk):
    "Eliminar categoría."
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        if category.products.exists():
            messages.error(request, f'No se puede eliminar la categoría {category.name} porque tiene productos asociados.')
            return redirect('category_list')
        name = category.name
        category.delete()
        messages.success(request, f'Categoría {name} eliminada.')
        return redirect('category_list')
    return render(request, 'inventory/confirm_delete.html', {'object': category, 'type': 'Categoría'})


# ------------------------------------------------------------------------------
# MOVIMIENTOS DE STOCK (ENTRADAS / SALIDAS)
# ------------------------------------------------------------------------------

@login_required(login_url='login')
def transaction_list_view(request):
    "Historial completo de movimientos de stock con filtros."
    tx_type = request.GET.get('type', '')
    product_id = request.GET.get('product', '')
    user_id = request.GET.get('user', '')

    transactions = StockTransaction.objects.select_related('product', 'user').all().order_by('-created_at')

    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type.upper())
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    if user_id:
        transactions = transactions.filter(user_id=user_id)

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    products = Product.objects.all().order_by('name')
    users = CustomUser.objects.all().order_by('username')

    context = {
        'page_obj': page_obj,
        'products': products,
        'users': users,
        'selected_type': tx_type,
        'selected_product': product_id,
        'selected_user': user_id,
    }
    return render(request, 'inventory/transaction_list.html', context)


@login_required(login_url='login')
def transaction_create_view(request):
    "Registro de movimientos de stock (Accesible a Admin, Bodeguero y Operario)."
    initial = {}
    product_id = request.GET.get('product')
    if product_id:
        initial['product'] = product_id

    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(
                request,
                f'Movimiento registrado: {transaction.get_transaction_type_display()} de {transaction.quantity} unidad(es) de {transaction.product.name}. Nuevo stock: {transaction.product.stock_actual}'
            )
            return redirect('transaction_list')
    else:
        form = StockTransactionForm(initial=initial)

    products = Product.objects.all().order_by('name')
    return render(request, 'inventory/transaction_form.html', {'form': form, 'products': products})


# ------------------------------------------------------------------------------
# GESTIÓN DE USUARIOS (SOLO ADMINISTRADOR)
# ------------------------------------------------------------------------------

@admin_required
def user_list_view(request):
    "Listado y administración de usuarios (Exclusivo Admin)."
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')

    users = CustomUser.objects.all().order_by('-date_joined')

    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter.lower())

    return render(request, 'inventory/user_list.html', {
        'users': users,
        'query': query,
        'selected_role': role_filter,
        'roles': CustomUser.Role.choices
    })


@admin_required
def user_create_view(request):
    "Crear nuevo usuario (Exclusivo Admin)."
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario {user.username} creado con rol de {user.get_role_display()}.')
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'inventory/user_form.html', {'form': form, 'title': 'Nuevo Usuario'})


@admin_required
def user_update_view(request, pk):
    "Editar usuario y rol (Exclusivo Admin)."
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario {user.username} actualizado.')
            return redirect('user_list')
    else:
        form = CustomUserEditForm(instance=user)
    return render(request, 'inventory/user_form.html', {'form': form, 'target_user': user, 'title': 'Editar Usuario'})


@admin_required
def user_toggle_status_view(request, pk):
    "Activar/Desactivar usuario."
    user = get_object_or_404(CustomUser, pk=pk)
    if user == request.user:
        messages.error(request, 'No puedes desactivar tu propia cuenta activa.')
    else:
        user.is_active = not user.is_active
        user.save()
        status_text = 'activado' if user.is_active else 'desactivado'
        messages.success(request, f'Usuario {user.username} ha sido {status_text}.')
    return redirect('user_list')


# ------------------------------------------------------------------------------
# PERFIL DE USUARIO
# ------------------------------------------------------------------------------

@login_required(login_url='login')
def profile_view(request):
    "Consulta y edición de datos del usuario autenticado."
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)

    my_transactions = user.stock_transactions.select_related('product').all()[:10]
    return render(request, 'inventory/profile.html', {'form': form, 'my_transactions': my_transactions})


# ==============================================================================
# VISTAS DE LA API REST (DRF & SIMPLEJWT)
# ==============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().order_by('id')
    permission_classes = [IsAuthenticated, IsAdminUserRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['id', 'username', 'role', 'date_joined']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return CustomUserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role.lower())
        return queryset

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        if request.method == 'PATCH':
            allowed_fields = ['first_name', 'last_name', 'email']
            for field in allowed_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()
            return Response(CustomUserSerializer(user).data)
        return Response(CustomUserSerializer(user).data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'description', 'category__name']
    ordering_fields = ['name', 'sku', 'price', 'stock_actual', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category')
        low_stock = self.request.query_params.get('low_stock')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if low_stock is not None:
            try:
                threshold = int(low_stock)
                queryset = queryset.filter(stock_actual__lte=threshold)
            except ValueError:
                pass

        return queryset

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, ProductCategoryPermission])
    def transactions(self, request, pk=None):
        product = self.get_object()
        transactions = product.transactions.select_related('user').all()
        serializer = StockTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.select_related('product', 'user').all().order_by('-created_at')
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated, StockTransactionPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__name', 'product__sku', 'user__username', 'notes']
    ordering_fields = ['created_at', 'quantity']

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product')
        tx_type = self.request.query_params.get('type')
        user_id = self.request.query_params.get('user')

        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type.upper())
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)