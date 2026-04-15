"""Modelos de datos para la calculadora de costos de importacion/exportacion.

Todos los campos monetarios usan decimal.Decimal para precision financiera exacta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def quantize_round(value: Decimal, places: int) -> Decimal:
    """Replica el comportamiento de ROUND() de Excel con ROUND_HALF_UP."""
    if places >= 0:
        exp = Decimal(10) ** -places
    else:
        exp = Decimal(10) ** (-places)
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def dec(value) -> Decimal:
    """Atajo para convertir cualquier valor a Decimal de forma segura."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# ---------------------------------------------------------------------------
# Factura Comercial (Paso 1)
# ---------------------------------------------------------------------------

@dataclass
class SkuLine:
    """Una linea de producto en la factura comercial."""
    name: str
    unit: str
    quantity: Decimal
    fob_unit_price: Decimal
    fob_total: Decimal = Decimal("0")
    proportion: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Tasas y Configuracion (Paso 2)
# ---------------------------------------------------------------------------

@dataclass
class ImportRates:
    """Tasas configurables para el calculo de importacion."""
    ad_valorem_rate: Decimal = Decimal("0.06")
    isc_rate: Decimal = Decimal("0")
    igv_rate: Decimal = Decimal("0.16")
    ipm_rate: Decimal = Decimal("0.02")
    insurance_rate: Decimal = Decimal("0.012")
    insurance_fee_rate: Decimal = Decimal("0.015")
    broker_commission_rate: Decimal = Decimal("0.01")
    broker_min_usd: Decimal = Decimal("100")
    igv_perception_rate: Decimal = Decimal("0.035")
    standard_igv: Decimal = Decimal("0.18")
    exchange_rate: Decimal = Decimal("3.72")


# ---------------------------------------------------------------------------
# Tributos Aduaneros (Paso 3)
# ---------------------------------------------------------------------------

@dataclass
class CustomsTaxResult:
    """Resultado del calculo de tributos aduaneros."""
    fob: Decimal = Decimal("0")
    freight: Decimal = Decimal("0")
    cfr: Decimal = Decimal("0")
    insurance: Decimal = Decimal("0")
    insurance_premium: Decimal = Decimal("0")
    cif: Decimal = Decimal("0")
    ad_valorem: Decimal = Decimal("0")
    isc: Decimal = Decimal("0")
    igv: Decimal = Decimal("0")
    ipm: Decimal = Decimal("0")
    total_taxes: Decimal = Decimal("0")
    igv_perception: Decimal = Decimal("0")
    broker_fee: Decimal = Decimal("0")
    total_deuda_aduanera: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Gastos de Importacion (Paso 4)
# ---------------------------------------------------------------------------

@dataclass
class ExpenseLine:
    """Una linea de gasto de importacion."""
    key: str
    label: str
    amount_usd: Decimal = Decimal("0")


@dataclass
class ImportExpenses:
    """Resultado del calculo de gastos de importacion."""
    lines: list[ExpenseLine] = field(default_factory=list)
    subtotal_expenses: Decimal = Decimal("0")
    igv_on_expenses: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Asignacion por Producto (Paso 5)
# ---------------------------------------------------------------------------

@dataclass
class SkuCostAllocation:
    """Desglose de costos asignados a un SKU."""
    sku: SkuLine
    allocated_cif: Decimal = Decimal("0")
    allocated_taxes: Decimal = Decimal("0")
    allocated_expenses: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Precio de Venta (Paso 6)
# ---------------------------------------------------------------------------

@dataclass
class SkuSellingPrice:
    """Precio de venta calculado para un SKU."""
    sku_name: str
    unit_cost: Decimal = Decimal("0")
    margin_percent: Decimal = Decimal("0.30")
    retail_price_ex_igv: Decimal = Decimal("0")
    igv_on_price: Decimal = Decimal("0")
    retail_price_inc_igv: Decimal = Decimal("0")
    profit_per_unit: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Costos de Exportacion (Paso 7)
# ---------------------------------------------------------------------------

@dataclass
class ExportExpenseLine:
    """Una linea de gasto de exportacion."""
    key: str
    label: str
    amount_usd: Decimal = Decimal("0")


@dataclass
class ExportCostResult:
    """Resultado del calculo de costos de exportacion."""
    fob_total: Decimal = Decimal("0")
    lines: list[ExportExpenseLine] = field(default_factory=list)
    total_logistics: Decimal = Decimal("0")
    total_documentation: Decimal = Decimal("0")
    total_export_cost: Decimal = Decimal("0")
    fob_net: Decimal = Decimal("0")
    num_skus: int = 0


@dataclass
class SkuExportAllocation:
    """Desglose de costos de exportacion asignados a un SKU."""
    sku: SkuLine
    allocated_export_cost: Decimal = Decimal("0")
    unit_export_cost: Decimal = Decimal("0")
    fob_net_per_unit: Decimal = Decimal("0")
