"""Modulo de contratos: import/export de trade-case.v1 y trade-costs.v1.

Provee funciones para:
- Cargar un caso de importacion desde JSON (trade-case.v1 o formato legacy palletizer).
- Exportar los resultados de calculo a JSON (trade-costs.v1).
- Persistir resultados en disco con formato legible.

Todos los valores monetarios se transportan como strings en JSON para
preservar la precision exacta de Decimal.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import IO, Any, Union

from engine.models import (
    CustomsTaxResult,
    ExportCostResult,
    ImportExpenses,
    ImportRates,
    SkuCostAllocation,
    SkuExportAllocation,
    SkuLine,
    SkuSellingPrice,
    dec,
)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TRADE_CASE_VERSION = "trade-case.v1"
TRADE_COSTS_VERSION = "trade-costs.v1"

REGULATORY_BASIS_PERU: dict[str, Any] = {
    "country": "PE",
    "ratesValidAsOf": None,  # se llena al momento de exportar con la fecha actual
    "legalReferences": [
        "Ley General de Aduanas (D.L. 1053)",
        "Reglamento LGA (D.S. 010-2009-EF)",
        "Arancel de Aduanas (D.S. 342-2016-EF)",
        "TUO Ley IGV e ISC (D.S. 055-99-EF)",
        "Regimen de Percepciones (Ley 29173)",
    ],
    "exchangeRateSource": "SBS",
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _decimal_to_str(d: Decimal) -> str:
    """Convierte un Decimal a string preservando la precision original.

    >>> _decimal_to_str(Decimal("123.4500"))
    '123.4500'
    """
    return str(d)


def _read_json(file_or_dict: Union[str, Path, IO[str], dict]) -> dict:
    """Lee JSON desde distintas fuentes y devuelve un dict.

    Acepta:
    - ``dict``: se devuelve directamente.
    - ``str`` o ``Path``: se interpreta como ruta a archivo.
    - Objeto file-like con metodo ``read()``: se lee y parsea.

    Raises:
        TypeError: si el tipo de entrada no es soportado.
        json.JSONDecodeError: si el contenido no es JSON valido.
        FileNotFoundError: si la ruta no existe.
    """
    if isinstance(file_or_dict, dict):
        return file_or_dict

    if isinstance(file_or_dict, (str, Path)):
        path = Path(file_or_dict)
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)  # type: ignore[no-any-return]

    # File-like object
    if hasattr(file_or_dict, "read"):
        content = file_or_dict.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        return json.loads(content)  # type: ignore[no-any-return]

    raise TypeError(
        f"Se esperaba str, Path, file-like o dict; se recibio {type(file_or_dict).__name__}"
    )


def _safe_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Convierte un valor a Decimal de forma segura, con fallback a *default*."""
    if value is None:
        return default
    try:
        return dec(value)
    except (InvalidOperation, ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Importar: trade-case.v1
# ---------------------------------------------------------------------------

def load_trade_case(
    file_or_dict: Union[str, Path, IO[str], dict],
) -> tuple[str, list[SkuLine], dict[str, Any]]:
    """Carga un archivo trade-case.v1 y devuelve los objetos de dominio.

    Parameters
    ----------
    file_or_dict:
        Ruta a un archivo JSON, objeto file-like abierto para lectura,
        o un ``dict`` ya parseado.

    Returns
    -------
    tuple[str, list[SkuLine], dict]
        ``(case_id, skus, metadata)`` donde:
        - *case_id*: identificador unico del caso.
        - *skus*: lista de :class:`SkuLine` listos para calcular.
        - *metadata*: diccionario con campos complementarios del caso
          (company, operationType, origin, destination, incoterm,
          modePreference, packagingSummary, palletSummary,
          containerSummary, skuIds).

    Raises
    ------
    ValueError
        Si la version no es ``trade-case.v1`` o no hay SKUs definidos.
    """
    data = _read_json(file_or_dict)

    # -- Validar version --------------------------------------------------
    version = data.get("version")
    if version != TRADE_CASE_VERSION:
        raise ValueError(
            f"Version incompatible: se esperaba '{TRADE_CASE_VERSION}', "
            f"se recibio '{version}'"
        )

    # -- Identificador del caso -------------------------------------------
    case_id: str = data.get("caseId") or str(uuid.uuid4())

    # -- SKUs -------------------------------------------------------------
    raw_skus: list[dict[str, Any]] = data.get("skus", [])
    if not raw_skus:
        raise ValueError("El caso no contiene SKUs (campo 'skus' vacio o ausente).")

    skus: list[SkuLine] = []
    sku_ids: list[str | None] = []

    for item in raw_skus:
        sku = SkuLine(
            name=str(item.get("name", "Sin nombre")),
            unit=str(item.get("unit", "UND")),
            quantity=_safe_decimal(item.get("quantity"), Decimal("0")),
            fob_unit_price=_safe_decimal(item.get("fobUnitPrice"), Decimal("0")),
        )
        skus.append(sku)
        sku_ids.append(item.get("skuId"))

    # -- Metadata complementaria ------------------------------------------
    _metadata_keys = (
        "company",
        "operationType",
        "originCountry",
        "destinationCountry",
        "origin",           # legacy compat (palletizer pre-schema)
        "destination",      # legacy compat (palletizer pre-schema)
        "incoterm",
        "modePreference",
        "packagingSummary",
        "palletSummary",
        "containerSummary",
    )
    metadata: dict[str, Any] = {
        key: data[key] for key in _metadata_keys if key in data
    }
    # Guardar los skuIds para round-trip
    metadata["skuIds"] = sku_ids

    return case_id, skus, metadata


# ---------------------------------------------------------------------------
# Importar: formato legacy palletizer
# ---------------------------------------------------------------------------

def load_palletizer_legacy(
    file_or_dict: Union[str, Path, IO[str], dict],
) -> tuple[str | None, list[SkuLine], dict[str, Any]]:
    """Carga un JSON en formato legacy palletizer y extrae los SKUs.

    El formato legacy almacena la informacion en
    ``input.multiSkuInputs[]``.  Como este formato no incluye precios
    FOB, todos los ``fob_unit_price`` se inicializan en 0 (el usuario
    debe completarlos manualmente).

    Parameters
    ----------
    file_or_dict:
        Ruta a un archivo JSON, objeto file-like abierto para lectura,
        o un ``dict`` ya parseado.

    Returns
    -------
    tuple[str | None, list[SkuLine], dict]
        ``(case_id, skus, metadata)`` donde *case_id* es ``None``
        para el formato legacy.

    Raises
    ------
    ValueError
        Si no se encuentran SKUs en ``input.multiSkuInputs``.
    """
    data = _read_json(file_or_dict)

    # -- Navegar a la lista de SKUs legacy --------------------------------
    input_block: dict[str, Any] = data.get("input", {})
    raw_skus: list[dict[str, Any]] = input_block.get("multiSkuInputs", [])

    if not raw_skus:
        raise ValueError(
            "No se encontraron SKUs en 'input.multiSkuInputs' del formato legacy."
        )

    skus: list[SkuLine] = []
    for item in raw_skus:
        name = (
            item.get("name")
            or item.get("skuName")
            or item.get("productName")
            or "Sin nombre"
        )
        unit = item.get("unit") or item.get("unitType") or "UND"
        quantity = _safe_decimal(
            item.get("quantity") or item.get("qty"),
            Decimal("0"),
        )
        sku = SkuLine(
            name=str(name),
            unit=str(unit),
            quantity=quantity,
            fob_unit_price=Decimal("0"),
        )
        skus.append(sku)

    # -- Metadata: extraer lo que el formato legacy permita ---------------
    metadata: dict[str, Any] = {}
    if "output" in data:
        metadata["legacyOutput"] = data["output"]
    if "containerType" in input_block:
        metadata["containerType"] = input_block["containerType"]
    if "palletType" in input_block:
        metadata["palletType"] = input_block["palletType"]

    return None, skus, metadata


# ---------------------------------------------------------------------------
# Exportar: trade-costs.v1
# ---------------------------------------------------------------------------

def export_trade_costs(
    *,
    case_id: str,
    rates: ImportRates,
    customs: CustomsTaxResult,
    expenses: ImportExpenses,
    allocations: list[SkuCostAllocation],
    prices: list[SkuSellingPrice],
    export_result: ExportCostResult | None = None,
    export_allocations: list[SkuExportAllocation] | None = None,
    exchange_rate: Decimal,
    regulatory_basis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Genera un dict conforme al esquema trade-costs.v1.

    Todos los valores :class:`~decimal.Decimal` se serializan como
    strings para preservar precision exacta en el transporte JSON.

    Parameters
    ----------
    case_id:
        Identificador del caso que origino el calculo.
    rates:
        Tasas de importacion utilizadas.
    customs:
        Resultado del calculo de tributos aduaneros.
    expenses:
        Resultado del calculo de gastos de importacion.
    allocations:
        Desglose de costos asignados por SKU.
    prices:
        Precios de venta calculados por SKU.
    export_result:
        Resultado del calculo de exportacion (opcional).
    export_allocations:
        Desglose de costos de exportacion por SKU (opcional).
    exchange_rate:
        Tipo de cambio USD/PEN utilizado.
    regulatory_basis:
        Base regulatoria. Si es ``None`` se usan los valores por
        defecto de Peru (:data:`REGULATORY_BASIS_PERU`).

    Returns
    -------
    dict
        Diccionario listo para serializar a JSON.
    """
    now = datetime.now(timezone.utc)

    # -- Base regulatoria -------------------------------------------------
    reg = _build_regulatory_basis(regulatory_basis, now)

    # -- Documento raiz ---------------------------------------------------
    doc: dict[str, Any] = {
        "version": TRADE_COSTS_VERSION,
        "caseId": case_id or str(uuid.uuid4()),
        "currency": "USD",
        "localCurrency": "PEN",
        "generatedAt": now.isoformat(),
        "sourceModule": "import-cost-calculator",
        "exchangeRate": _decimal_to_str(exchange_rate),
        "regulatoryBasis": reg,
        "rates": _serialize_rates(rates),
        "customs": _serialize_customs(customs),
        "expenses": _serialize_expenses(expenses),
        "allocationsBySku": [
            _serialize_allocation(a, idx) for idx, a in enumerate(allocations)
        ],
        "pricing": [_serialize_price(p, idx) for idx, p in enumerate(prices)],
    }

    # -- Secciones opcionales de exportacion ------------------------------
    if export_result is not None:
        export_costs_dict = _serialize_export_result(export_result)
        if export_allocations:
            export_costs_dict["allocationsBySku"] = [
                _serialize_export_allocation(ea, idx)
                for idx, ea in enumerate(export_allocations)
            ]
        doc["exportCosts"] = export_costs_dict

    return doc


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def save_trade_costs(data: dict[str, Any], path: Union[str, Path]) -> Path:
    """Escribe el resultado trade-costs.v1 como JSON formateado.

    Parameters
    ----------
    data:
        Diccionario generado por :func:`export_trade_costs`.
    path:
        Ruta destino del archivo JSON.

    Returns
    -------
    Path
        Ruta absoluta del archivo escrito.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return target.resolve()


# ---------------------------------------------------------------------------
# Serializadores internos
# ---------------------------------------------------------------------------

def _build_regulatory_basis(
    override: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    """Construye la seccion regulatoryBasis del documento."""
    if override is not None:
        basis = dict(override)
    else:
        basis = dict(REGULATORY_BASIS_PERU)
    # Siempre completar la fecha de vigencia si esta vacia
    if basis.get("ratesValidAsOf") is None:
        basis["ratesValidAsOf"] = now.date().isoformat()
    return basis


def _serialize_rates(rates: ImportRates) -> dict[str, str]:
    """Serializa las tasas de importacion a strings."""
    return {
        "adValoremRate": _decimal_to_str(rates.ad_valorem_rate),
        "iscRate": _decimal_to_str(rates.isc_rate),
        "igvRate": _decimal_to_str(rates.igv_rate),
        "ipmRate": _decimal_to_str(rates.ipm_rate),
        "insuranceRate": _decimal_to_str(rates.insurance_rate),
        "insuranceFeeRate": _decimal_to_str(rates.insurance_fee_rate),
        "brokerCommissionRate": _decimal_to_str(rates.broker_commission_rate),
        "brokerMinUsd": _decimal_to_str(rates.broker_min_usd),
        "igvPerceptionRate": _decimal_to_str(rates.igv_perception_rate),
        "standardIgv": _decimal_to_str(rates.standard_igv),
    }


def _serialize_customs(customs: CustomsTaxResult) -> dict[str, str]:
    """Serializa los tributos aduaneros a strings."""
    return {
        "fob": _decimal_to_str(customs.fob),
        "freight": _decimal_to_str(customs.freight),
        "cfr": _decimal_to_str(customs.cfr),
        "insurance": _decimal_to_str(customs.insurance),
        "insurancePremium": _decimal_to_str(customs.insurance_premium),
        "cif": _decimal_to_str(customs.cif),
        "adValorem": _decimal_to_str(customs.ad_valorem),
        "isc": _decimal_to_str(customs.isc),
        "igv": _decimal_to_str(customs.igv),
        "ipm": _decimal_to_str(customs.ipm),
        "totalTaxes": _decimal_to_str(customs.total_taxes),
        "igvPerception": _decimal_to_str(customs.igv_perception),
        "brokerFee": _decimal_to_str(customs.broker_fee),
        "totalDeudaAduanera": _decimal_to_str(customs.total_deuda_aduanera),
    }


def _serialize_expenses(expenses: ImportExpenses) -> dict[str, Any]:
    """Serializa los gastos de importacion."""
    return {
        "lines": [
            {
                "key": line.key,
                "label": line.label,
                "amountUsd": _decimal_to_str(line.amount_usd),
            }
            for line in expenses.lines
        ],
        "subtotalExpenses": _decimal_to_str(expenses.subtotal_expenses),
        "igvOnExpenses": _decimal_to_str(expenses.igv_on_expenses),
        "totalExpenses": _decimal_to_str(expenses.total_expenses),
    }


def _serialize_allocation(alloc: SkuCostAllocation, index: int = 0) -> dict[str, str]:
    """Serializa la asignacion de costos por SKU."""
    return {
        "skuId": f"SKU-{index + 1}",
        "skuName": alloc.sku.name,
        "unit": alloc.sku.unit,
        "quantity": _decimal_to_str(alloc.sku.quantity),
        "fobUnitPrice": _decimal_to_str(alloc.sku.fob_unit_price),
        "fobTotal": _decimal_to_str(alloc.sku.fob_total),
        "proportion": _decimal_to_str(alloc.sku.proportion),
        "allocatedCif": _decimal_to_str(alloc.allocated_cif),
        "allocatedTaxes": _decimal_to_str(alloc.allocated_taxes),
        "allocatedExpenses": _decimal_to_str(alloc.allocated_expenses),
        "totalCost": _decimal_to_str(alloc.total_cost),
        "unitCost": _decimal_to_str(alloc.unit_cost),
    }


def _serialize_price(price: SkuSellingPrice, index: int = 0) -> dict[str, str]:
    """Serializa el precio de venta por SKU."""
    return {
        "skuId": f"SKU-{index + 1}",
        "skuName": price.sku_name,
        "unitCost": _decimal_to_str(price.unit_cost),
        "marginPercent": _decimal_to_str(price.margin_percent),
        "retailPriceExIgv": _decimal_to_str(price.retail_price_ex_igv),
        "igvOnPrice": _decimal_to_str(price.igv_on_price),
        "retailPriceIncIgv": _decimal_to_str(price.retail_price_inc_igv),
        "profitPerUnit": _decimal_to_str(price.profit_per_unit),
    }


def _serialize_export_result(result: ExportCostResult) -> dict[str, Any]:
    """Serializa el resultado de costos de exportacion."""
    return {
        "fobTotal": _decimal_to_str(result.fob_total),
        "lines": [
            {
                "key": line.key,
                "label": line.label,
                "amountUsd": _decimal_to_str(line.amount_usd),
            }
            for line in result.lines
        ],
        "totalLogistics": _decimal_to_str(result.total_logistics),
        "totalDocumentation": _decimal_to_str(result.total_documentation),
        "totalExportCost": _decimal_to_str(result.total_export_cost),
        "fobNet": _decimal_to_str(result.fob_net),
        "numSkus": result.num_skus,
    }


def _serialize_export_allocation(alloc: SkuExportAllocation, index: int = 0) -> dict[str, str]:
    """Serializa la asignacion de costos de exportacion por SKU."""
    return {
        "skuId": f"SKU-{index + 1}",
        "skuName": alloc.sku.name,
        "unit": alloc.sku.unit,
        "quantity": _decimal_to_str(alloc.sku.quantity),
        "allocatedExportCost": _decimal_to_str(alloc.allocated_export_cost),
        "unitExportCost": _decimal_to_str(alloc.unit_export_cost),
        "fobNetPerUnit": _decimal_to_str(alloc.fob_net_per_unit),
    }
