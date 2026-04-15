"""Paso 3: Calculo de tributos aduaneros (CIF, Ad-Valorem, ISC, IGV, IPM)."""

from decimal import Decimal
from engine.models import ImportRates, CustomsTaxResult, quantize_round


def compute_customs(
    fob: Decimal,
    freight: Decimal,
    rates: ImportRates,
) -> CustomsTaxResult:
    """Calcula la cascada completa de tributos aduaneros.

    Replica las formulas exactas de las hojas Excel (CCi VF 06.04.26):
      CIF = FOB + Flete + Seguro
      Ad-Valorem = ROUND(CIF * tasa, 0)                        [F17]
      ISC = ROUND(CIF * tasa_isc, 0)                           [F19]
      IGV = ROUND((CIF + Ad-Valorem + ISC) * tasa_igv, 0)      [F18]
      IPM = ROUND((CIF + Ad-Valorem + ISC) * tasa_ipm, 0)      [F19]

    NOTA: Excel usa cascada donde ISC se suma a la base antes de IGV/IPM.
    """
    cfr = fob + freight

    insurance = quantize_round(cfr * rates.insurance_rate, 2)
    insurance_premium = quantize_round(insurance * rates.insurance_fee_rate, 2)

    cif = cfr + insurance

    ad_valorem = quantize_round(cif * rates.ad_valorem_rate, 0)

    # ISC se calcula sobre CIF (sin ad-valorem en la base original del Excel)
    isc = quantize_round(cif * rates.isc_rate, 0)

    # IGV e IPM incluyen ISC en su base (cascada del Excel)
    base_igv_ipm = cif + ad_valorem + isc
    igv = quantize_round(base_igv_ipm * rates.igv_rate, 0)
    ipm = quantize_round(base_igv_ipm * rates.ipm_rate, 0)

    total_taxes = ad_valorem + isc + igv + ipm

    igv_perception = quantize_round(
        (cif + total_taxes) * rates.igv_perception_rate, 2
    )

    broker_min_pen = rates.broker_min_usd
    broker_min_usd = quantize_round(broker_min_pen / rates.exchange_rate, 2)
    broker_fee = max(
        quantize_round(cif * rates.broker_commission_rate, 2),
        broker_min_usd,
    )

    total_deuda = total_taxes + igv_perception

    return CustomsTaxResult(
        fob=fob,
        freight=freight,
        cfr=cfr,
        insurance=insurance,
        insurance_premium=insurance_premium,
        cif=cif,
        ad_valorem=ad_valorem,
        isc=isc,
        igv=igv,
        ipm=ipm,
        total_taxes=total_taxes,
        igv_perception=igv_perception,
        broker_fee=broker_fee,
        total_deuda_aduanera=total_deuda,
    )
