import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Product, StockTransaction

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StockTransaction)
def update_product_stock_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        product = Product.objects.select_for_update().get(pk=instance.product_id)
        if instance.transaction_type == StockTransaction.TransactionType.ENTRADA:
            product.stock_actual += instance.quantity
        elif instance.transaction_type == StockTransaction.TransactionType.SALIDA:
            if product.stock_actual < instance.quantity:
                raise ValidationError(f'Stock insuficiente para producto {product.name}.')
            product.stock_actual -= instance.quantity
        product.save(update_fields=['stock_actual', 'updated_at'])


@receiver(post_delete, sender=StockTransaction)
def revert_product_stock_on_delete(sender, instance, **kwargs):
    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=instance.product_id)
            if instance.transaction_type == StockTransaction.TransactionType.ENTRADA:
                product.stock_actual = max(0, product.stock_actual - instance.quantity)
            elif instance.transaction_type == StockTransaction.TransactionType.SALIDA:
                product.stock_actual += instance.quantity
            product.save(update_fields=['stock_actual', 'updated_at'])
    except Product.DoesNotExist:
        pass
