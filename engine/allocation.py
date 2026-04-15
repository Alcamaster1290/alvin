"""Paso 5: Prorrateo de costos por producto (proporcional al FOB)."""

from decimal import Decimal
from engine.models import (
    SkuLine,
    CustomsTaxResult,
    ImportExpenses,
    SkuCostAllocation,
    quantize_round,
)


def allocate_costs(
    skus: list[SkuLine],
    customs: CustomsTaxResult,
    expenses: ImportExpenses,
) -> list[SkuCostAllocation]:
    """Distribuye CIF, tributos y gastos a cada SKU segun su proporcion FOB.

    Costo unitario = (CIF + tributos + gastos) * proporcion_SKU / cantidad_SKU
    """
    total_landed = (
        customs.cif
        + customs.total_taxes
        + customs.igv_perception
        + customs.broker_fee
        + expenses.total_expenses
    )

    allocations: list[SkuCostAllocation] = []

    for sku in skus:
        if sku.proportion == 0 or sku.quantity == 0:
            allocations.append(SkuCostAllocation(sku=sku))
            continue

        alloc_cif = quantize_round(customs.cif * sku.proportion, 2)
        alloc_taxes = quantize_round(
            (customs.total_taxes + customs.igv_perception + customs.broker_fee)
            * sku.proportion,
            2,
        )
        alloc_expenses = quantize_round(
            expenses.total_expenses * sku.proportion, 2
        )
        total_cost = alloc_cif + alloc_taxes + alloc_expenses
        unit_cost = quantize_round(total_cost / sku.quantity, 4)

        allocations.append(
            SkuCostAllocation(
                sku=sku,
                allocated_cif=alloc_cif,
                allocated_taxes=alloc_taxes,
                allocated_expenses=alloc_expenses,
                total_cost=total_cost,
                unit_cost=unit_cost,
            )
        )

    return allocations
