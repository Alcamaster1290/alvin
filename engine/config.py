"""Configuracion por defecto para tasas de importacion Peru."""

from decimal import Decimal
from engine.models import ImportRates


def default_peru_rates() -> ImportRates:
    """Retorna las tasas estandar para importacion en Peru."""
    return ImportRates(
        ad_valorem_rate=Decimal("0.06"),
        isc_rate=Decimal("0"),
        igv_rate=Decimal("0.16"),
        ipm_rate=Decimal("0.02"),
        insurance_rate=Decimal("0.012"),
        insurance_fee_rate=Decimal("0.015"),
        broker_commission_rate=Decimal("0.01"),
        broker_min_usd=Decimal("100"),
        igv_perception_rate=Decimal("0.035"),
        standard_igv=Decimal("0.18"),
        exchange_rate=Decimal("3.72"),
    )
