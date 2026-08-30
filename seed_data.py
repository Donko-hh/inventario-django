import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import CustomUser, Category, Product, StockTransaction

def seed():
    # 1. Crear usuarios de los 3 perfiles
    users = [
        ('admin', 'admin@empresa.com', 'admin123', 'admin', 'Carlos', 'Administrador', True),
        ('bodeguero', 'bodega@empresa.com', 'bodega123', 'bodeguero', 'Miguel', 'Jefe de Bodega', False),
        ('operario', 'operario@empresa.com', 'operario123', 'operario', 'Juan', 'Operario', False),
    ]

    for username, email, pwd, role, fname, lname, is_super in users:
        user, created = CustomUser.objects.get_or_create(username=username, defaults={
            'email': email,
            'role': role,
            'first_name': fname,
            'last_name': lname,
            'is_staff': True if (role == 'admin' or is_super) else False,
            'is_superuser': is_super
        })
        user.set_password(pwd)
        user.role = role
        user.save()
        status = 'creado' if created else 'actualizado'
        print(f'Usuario {username} ({role}) {status}')

    # 2. Crear Categorias
    cat_comp, _ = Category.objects.get_or_create(name='Computacion', defaults={'description': 'Equipos de computo, laptops y perifericos'})
    cat_redes, _ = Category.objects.get_or_create(name='Redes y Telecomunicaciones', defaults={'description': 'Routers, switches, cableado y antenas'})
    cat_audio, _ = Category.objects.get_or_create(name='Audio y Video', defaults={'description': 'Monitores, proyectores y sistemas de sonido'})
    cat_oficina, _ = Category.objects.get_or_create(name='Suministros de Oficina', defaults={'description': 'Papeleria, tintas y accesorios'})

    # 3. Crear Productos
    admin_user = CustomUser.objects.get(username='admin')

    prod1, _ = Product.objects.get_or_create(
        sku='LAP-LEN-001',
        defaults={
            'name': 'Laptop Lenovo ThinkPad T14',
            'category': cat_comp,
            'price': 1250.00,
            'description': 'Laptop profesional 14 pulgadas, Core i7, 16GB RAM, 512GB SSD'
        }
    )
    prod2, _ = Product.objects.get_or_create(
        sku='MON-DEL-027',
        defaults={
            'name': 'Monitor Dell UltraSharp 27 4K',
            'category': cat_audio,
            'price': 480.00,
            'description': 'Monitor IPS 4K UHD con conectividad USB-C'
        }
    )
    prod3, _ = Product.objects.get_or_create(
        sku='SW-CIS-024',
        defaults={
            'name': 'Switch Cisco Catalyst 24 Puertos Gigabit',
            'category': cat_redes,
            'price': 890.00,
            'description': 'Switch administrable Layer 2/3 con PoE+'
        }
    )
    prod4, _ = Product.objects.get_or_create(
        sku='MOU-LOG-MX3',
        defaults={
            'name': 'Mouse Inalambrico Logitech MX Master 3S',
            'category': cat_comp,
            'price': 99.00,
            'description': 'Mouse ergonomico de alta precision con sensor de 8000 DPI'
        }
    )

    # 4. Transacciones iniciales para dar stock
    if prod1.stock_actual == 0:
        StockTransaction.objects.create(product=prod1, transaction_type='ENTRADA', quantity=15, user=admin_user, notes='Inventario inicial de apertura')
    if prod2.stock_actual == 0:
        StockTransaction.objects.create(product=prod2, transaction_type='ENTRADA', quantity=8, user=admin_user, notes='Recepcion lote proveedores')
    if prod3.stock_actual == 0:
        StockTransaction.objects.create(product=prod3, transaction_type='ENTRADA', quantity=3, user=admin_user, notes='Stock critico inicial')
    if prod4.stock_actual == 0:
        StockTransaction.objects.create(product=prod4, transaction_type='ENTRADA', quantity=25, user=admin_user, notes='Compra por volumen')

    print('Base de datos poblada exitosamente con datos de prueba.')

if __name__ == '__main__':
    seed()
