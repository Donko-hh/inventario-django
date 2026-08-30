from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrador')
        BODEGUERO = 'bodeguero', _('Jefe de Bodega')
        OPERARIO = 'operario', _('Operario')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERARIO,
        verbose_name=_('Rol'),
        help_text=_('Define el perfil de acceso y permisos dentro del sistema.')
    )

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['id']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_admin_role(self):
        return self.role.lower() == self.Role.ADMIN or self.is_superuser

    @property
    def is_bodeguero_role(self):
        return self.role.lower() == self.Role.BODEGUERO

    @property
    def is_operario_role(self):
        return self.role.lower() == self.Role.OPERARIO

    def save(self, *args, **kwargs):
        if self.role:
            self.role = self.role.lower()
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Nombre')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripción')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )

    class Meta:
        verbose_name = _('Categoría')
        verbose_name_plural = _('Categorías')
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Categoría')
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_('Nombre del Producto')
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_('Código SKU')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripción')
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Precio Unitario')
    )
    stock_actual = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Stock Actual'),
        help_text=_('Actualizado automáticamente mediante transacciones de stock.')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )

    class Meta:
        verbose_name = _('Producto')
        verbose_name_plural = _('Productos')
        ordering = ['name']

    def __str__(self):
        return f'{self.sku} - {self.name} (Stock: {self.stock_actual})'


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        ENTRADA = 'ENTRADA', _('Entrada')
        SALIDA = 'SALIDA', _('Salida')

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name=_('Producto')
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        verbose_name=_('Tipo de Movimiento')
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Cantidad')
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='stock_transactions',
        verbose_name=_('Usuario Responsable')
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Motivo / Notas')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha y Hora')
    )

    class Meta:
        verbose_name = _('Transacción de Stock')
        verbose_name_plural = _('Transacciones de Stock')
        ordering = ['-created_at']

    def __str__(self):
        date_str = self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else 'Reciente'
        return f'{self.get_transaction_type_display()}: {self.quantity} x {self.product.name} ({date_str})'
