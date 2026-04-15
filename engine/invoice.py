"""Paso 1: Calculo de factura comercial (FOB y proporciones por SKU)."""

from decimal import Decimal
from engine.models import SkuLine


def compute_invoice(skus: list[SkuLine]) -> list[SkuLine]:
    """Calcula FOB total y proporcion de cada SKU sobre el total."""
    for sku in skus:
        sku.fob_total = sku.quantity * sku.fob_unit_price

    total_fob = sum(s.fob_total for s in skus)

    for sku in skus:
        if total_fob > 0:
            sku.proportion = sku.fob_total / total_fob
        else:
            sku.proportion = Decimal("0")

    return skus


def get_total_fob(skus: list[SkuLine]) -> Decimal:
    """Retorna la suma de FOB de todos los SKUs."""
    return sum(s.fob_total for s in skus)
