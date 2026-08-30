from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from inventory.models import CustomUser, Category, Product, StockTransaction


class InventoryRBACAndStockTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Crear usuarios con los 3 perfiles
        self.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            password='Password123!',
            email='admin@inventario.com',
            role=CustomUser.Role.ADMIN,
            is_staff=True
        )

        self.bodeguero_user = CustomUser.objects.create_user(
            username='bodeguero_test',
            password='Password123!',
            email='bodeguero@inventario.com',
            role=CustomUser.Role.BODEGUERO
        )

        self.operario_user = CustomUser.objects.create_user(
            username='operario_test',
            password='Password123!',
            email='operario@inventario.com',
            role=CustomUser.Role.OPERARIO
        )

        # 2. Crear categoría y producto base
        self.category = Category.objects.create(
            name='Electrónica',
            description='Dispositivos y componentes electrónicos'
        )

        self.product = Product.objects.create(
            category=self.category,
            name='Laptop Gamer',
            sku='LAP-001',
            description='Laptop Core i7 16GB RAM',
            price=Decimal('1200.00'),
            stock_actual=0
        )

    # ==========================================
    # TESTS DE AUTENTICACIÓN JWT
    # ==========================================
    def test_jwt_login_returns_tokens_and_user_data(self):
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'admin_test',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'admin_test')
        self.assertEqual(response.data['user']['role'], 'admin')

    # ==========================================
    # TESTS DE PERMISOS RBAC: USUARIOS
    # ==========================================
    def test_admin_can_manage_users(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Crear nuevo usuario
        create_resp = self.client.post('/api/users/', {
            'username': 'nuevo_operario',
            'password': 'Password123!',
            'email': 'nuevo@inventario.com',
            'role': 'OPERARIO'
        })
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

    def test_bodeguero_cannot_manage_users(self):
        self.client.force_authenticate(user=self.bodeguero_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operario_cannot_manage_users(self):
        self.client.force_authenticate(user=self.operario_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # TESTS DE PERMISOS RBAC: PRODUCTOS Y CATEGORÍAS
    # ==========================================
    def test_bodeguero_can_create_and_delete_products_and_categories(self):
        self.client.force_authenticate(user=self.bodeguero_user)

        # Crear Categoría
        cat_resp = self.client.post('/api/categories/', {
            'name': 'Hogar y Oficina',
            'description': 'Muebles y suministros'
        })
        self.assertEqual(cat_resp.status_code, status.HTTP_201_CREATED)
        cat_id = cat_resp.data['id']

        # Crear Producto
        prod_resp = self.client.post('/api/products/', {
            'category': cat_id,
            'name': 'Silla Ergonómica',
            'sku': 'SIL-001',
            'description': 'Silla de oficina ajustable',
            'price': '150.00'
        })
        self.assertEqual(prod_resp.status_code, status.HTTP_201_CREATED)
        prod_id = prod_resp.data['id']

        # Eliminar Producto
        del_prod_resp = self.client.delete(f'/api/products/{prod_id}/')
        self.assertEqual(del_prod_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_operario_can_read_catalog_but_cannot_create_or_delete(self):
        self.client.force_authenticate(user=self.operario_user)

        # Lectura permitida
        list_resp = self.client.get('/api/products/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        cat_list_resp = self.client.get('/api/categories/')
        self.assertEqual(cat_list_resp.status_code, status.HTTP_200_OK)

        # Creación denegada (403)
        create_cat_resp = self.client.post('/api/categories/', {
            'name': 'Nueva Categoria Prohibida'
        })
        self.assertEqual(create_cat_resp.status_code, status.HTTP_403_FORBIDDEN)

        create_prod_resp = self.client.post('/api/products/', {
            'category': self.category.id,
            'name': 'Teclado Mecanico',
            'sku': 'TEC-001',
            'price': '50.00'
        })
        self.assertEqual(create_prod_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Borrado denegado (403)
        del_resp = self.client.delete(f'/api/products/{self.product.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # TESTS DE MOVIMIENTOS Y AUTOMATIZACIÓN DE STOCK
    # ==========================================
    def test_operario_can_create_stock_transactions(self):
        self.client.force_authenticate(user=self.operario_user)

        # 1. Registrar Entrada de Stock
        entrada_resp = self.client.post('/api/transactions/', {
            'product': self.product.id,
            'transaction_type': 'ENTRADA',
            'quantity': 25,
            'notes': 'Llegada de lote inicial de importación'
        })
        self.assertEqual(entrada_resp.status_code, status.HTTP_201_CREATED)

        # Verificar que el stock se actualizó automáticamente
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 25)

        # 2. Registrar Salida de Stock
        salida_resp = self.client.post('/api/transactions/', {
            'product': self.product.id,
            'transaction_type': 'SALIDA',
            'quantity': 10,
            'notes': 'Despacho a cliente Orden #1024'
        })
        self.assertEqual(salida_resp.status_code, status.HTTP_201_CREATED)

        # Verificar decremento de stock
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 15)

    def test_salida_with_insufficient_stock_fails(self):
        self.client.force_authenticate(user=self.operario_user)

        # Intentar sacar 50 unidades cuando el stock es 0
        response = self.client.post('/api/transactions/', {
            'product': self.product.id,
            'transaction_type': 'SALIDA',
            'quantity': 50,
            'notes': 'Despacho que debe fallar'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', response.data)

        # Verificar que el stock sigue en 0
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 0)

    def test_operario_cannot_delete_or_modify_transactions(self):
        self.client.force_authenticate(user=self.admin_user)
        tx = StockTransaction.objects.create(
            product=self.product,
            transaction_type=StockTransaction.TransactionType.ENTRADA,
            quantity=10,
            user=self.admin_user
        )

        # Operario intenta modificar o borrar
        self.client.force_authenticate(user=self.operario_user)
        del_resp = self.client.delete(f'/api/transactions/{tx.id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

        put_resp = self.client.put(f'/api/transactions/{tx.id}/', {
            'product': self.product.id,
            'transaction_type': 'ENTRADA',
            'quantity': 20
        })
        self.assertEqual(put_resp.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # TESTS DE VISTAS WEB (MONOLITO TAILWIND)
    # ==========================================
    def test_web_login_and_dashboard_access(self):
        # Acceso no autenticado redirige a login
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

        # Iniciar sesión vía web
        login_success = self.client.login(username='admin_test', password='Password123!')
        self.assertTrue(login_success)

        dash_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertTemplateUsed(dash_resp, 'inventory/dashboard.html')

    def test_web_operario_restricted_from_product_creation(self):
        self.client.login(username='operario_test', password='Password123!')

        # Operario intenta acceder al formulario de crear producto -> denegado y redirigido a dashboard
        resp = self.client.get(reverse('product_create'))
        self.assertEqual(resp.status_code, 302)

    def test_web_operario_can_create_transaction(self):
        self.client.login(username='operario_test', password='Password123!')

        # Operario accede a formulario de transacción
        resp = self.client.get(reverse('transaction_create'))
        self.assertEqual(resp.status_code, 200)

        # Operario registra entrada de stock
        post_resp = self.client.post(reverse('transaction_create'), {
            'product': self.product.id,
            'transaction_type': 'ENTRADA',
            'quantity': 12,
            'notes': 'Entrada web operario'
        })
        self.assertEqual(post_resp.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 12)

