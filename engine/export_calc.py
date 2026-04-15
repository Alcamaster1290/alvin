"""Paso 7: Calculo de costos de exportacion."""

from decimal import Decimal
from engine.models import (
    SkuLine,
    ExportExpenseLine,
    ExportCostResult,
    SkuExportAllocation,
    quantize_round,
)


DEFAULT_EXPORT_EXPENSE_KEYS = [
    ("transporte_interno", "Transporte interno al puerto"),
    ("agente_aduanas", "Agente de aduanas (exportacion)"),
    ("cargos_portuarios", "Cargos portuarios / terminales"),
    ("documentacion", "Documentacion y certificados"),
    ("embalaje", "Embalaje y paletizacion"),
    ("certificaciones", "Certificaciones de origen / fitosanitarias"),
    ("seguro_interno", "Seguro de transporte interno"),
    ("almacenaje_puerto", "Almacenaje en puerto"),
    ("manipuleo_puerto", "Manipuleo en puerto"),
    ("visto_bueno", "Visto bueno (B/L fee)"),
    ("gastos_bancarios", "Gastos bancarios / carta de credito"),
    ("otros_export", "Otros gastos de exportacion"),
]


def create_default_export_expenses() -> list[ExportExpenseLine]:
    """Crea la lista de items de gastos de exportacion con valores en 0."""
    return [ExportExpenseLine(key=k, label=l) for k, l in DEFAULT_EXPORT_EXPENSE_KEYS]


def compute_export_costs(
    fob_total: Decimal,
    lines: list[ExportExpenseLine],
    num_skus: int = 0,
) -> ExportCostResult:
    """Calcula los costos totales de exportacion.

    FOB neto = FOB bruto - total gastos exportacion
    """
    logistics_keys = {
        "transporte_interno", "cargos_portuarios", "embalaje",
        "seguro_interno", "almacenaje_puerto", "manipuleo_puerto",
    }
    doc_keys = {
        "documentacion", "certificaciones", "visto_bueno",
        "gastos_bancarios",
    }

    total_logistics = Decimal("0")
    total_documentation = Decimal("0")
    total_all = Decimal("0")

    for line in lines:
        total_all += line.amount_usd
        if line.key in logistics_keys:
            total_logistics += line.amount_usd
        elif line.key in doc_keys:
            total_documentation += line.amount_usd

    fob_net = fob_total - total_all

    return ExportCostResult(
        fob_total=fob_total,
        lines=lines,
        total_logistics=total_logistics,
        total_documentation=total_documentation,
        total_export_cost=total_all,
        fob_net=fob_net,
        num_skus=num_skus,
    )


def allocate_export_costs(
    skus: list[SkuLine],
    export_result: ExportCostResult,
) -> list[SkuExportAllocation]:
    """Distribuye costos de exportacion a cada SKU segun su proporcion FOB."""
    allocations: list[SkuExportAllocation] = []

    for sku in skus:
        if sku.proportion == 0 or sku.quantity == 0:
            allocations.append(SkuExportAllocation(sku=sku))
            continue

        alloc_cost = quantize_round(
            export_result.total_export_cost * sku.proportion, 2
        )
        unit_cost = quantize_round(alloc_cost / sku.quantity, 4)
        fob_net_unit = quantize_round(
            (sku.fob_unit_price * sku.quantity - alloc_cost) / sku.quantity, 4
        )

        allocations.append(
            SkuExportAllocation(
                sku=sku,
                allocated_export_cost=alloc_cost,
                unit_export_cost=unit_cost,
                fob_net_per_unit=fob_net_unit,
            )
        )

    return allocations
