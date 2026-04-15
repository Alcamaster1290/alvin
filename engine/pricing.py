"""Paso 6: Calculo de precio de venta con margen."""

from decimal import Decimal
from engine.models import SkuCostAllocation, SkuSellingPrice, quantize_round


def compute_selling_prices(
    allocations: list[SkuCostAllocation],
    margins: dict[str, Decimal] | None = None,
    default_margin: Decimal = Decimal("0.40"),
    igv_rate: Decimal = Decimal("0.18"),
) -> list[SkuSellingPrice]:
    """Calcula el precio de venta para cada SKU.

    Formula Excel (CCi VF 06.04.26, Hoja 'Precio de Venta', celda H8):
      Precio sin IGV = Costo unitario / (1 - margen%)

    Esto interpreta el margen como porcentaje del precio de venta (no del costo).
    Ejemplo: margen 40% -> Costo 100 / (1 - 0.40) = 166.67 (margen = 66.67 del precio 166.67 = 40%)
    """
    if margins is None:
        margins = {}

    results: list[SkuSellingPrice] = []

    for alloc in allocations:
        margin = margins.get(alloc.sku.name, default_margin)
        unit_cost = alloc.unit_cost

        # Formula Excel: =IF(F8=0,0,F8/(1-G8))
        denominator = Decimal("1") - margin
        if denominator > 0:
            retail_ex = quantize_round(unit_cost / denominator, 4)
        else:
            retail_ex = Decimal("0")

        igv = quantize_round(retail_ex * igv_rate, 4)
        retail_inc = retail_ex + igv
        profit = retail_ex - unit_cost

        results.append(
            SkuSellingPrice(
                sku_name=alloc.sku.name,
                unit_cost=unit_cost,
                margin_percent=margin,
                retail_price_ex_igv=retail_ex,
                igv_on_price=igv,
                retail_price_inc_igv=retail_inc,
                profit_per_unit=profit,
            )
        )

    return results
