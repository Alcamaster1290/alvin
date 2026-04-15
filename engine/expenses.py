"""Paso 4: Calculo de gastos de importacion (21 items)."""

from decimal import Decimal
from engine.models import ExpenseLine, ImportExpenses, quantize_round


DEFAULT_EXPENSE_KEYS = [
    ("seguro_permiso", "Seguro / Permiso de importacion"),
    ("handling", "Handling (manipuleo)"),
    ("descarga", "Servicio de descarga"),
    ("traccion", "Traccion de carga"),
    ("movimiento_carga", "Movimiento de carga"),
    ("atencion_cliente", "Atencion al cliente"),
    ("gastos_operativos", "Gastos operativos"),
    ("almacenaje", "Almacenaje en deposito"),
    ("cuadrilla", "Cuadrilla de carga"),
    ("servicios_admin", "Servicios administrativos"),
    ("seguro_contenedor", "Seguro de contenedor"),
    ("posicionamiento", "Posicionamiento de carga"),
    ("transporte_interno", "Transporte interno (ultimo tramo)"),
    ("precintos", "Precintos / Sellos"),
    ("gastos_varios", "Gastos varios"),
    ("comision_agente", "Comision agente de aduana"),
    ("devolucion_contenedor", "Devolucion de contenedor"),
    ("aforo_fisico", "Gastos de aforo fisico"),
    ("almacen_extra", "Almacenaje extra / sobreestadia"),
    ("otros_1", "Otros gastos 1"),
    ("otros_2", "Otros gastos 2"),
]


def create_default_expenses() -> list[ExpenseLine]:
    """Crea la lista de 21 items de gastos con valores en 0."""
    return [ExpenseLine(key=k, label=l) for k, l in DEFAULT_EXPENSE_KEYS]


def compute_expenses(
    lines: list[ExpenseLine],
    igv_rate: Decimal = Decimal("0.18"),
) -> ImportExpenses:
    """Calcula el subtotal, IGV y total de gastos de importacion."""
    subtotal = sum(line.amount_usd for line in lines)
    igv = quantize_round(subtotal * igv_rate, 2)

    return ImportExpenses(
        lines=lines,
        subtotal_expenses=subtotal,
        igv_on_expenses=igv,
        total_expenses=subtotal + igv,
    )
