"""Tests for engine.customs -- Peruvian customs tax cascade.

This is the most critical test file: it validates the exact cascade of
CIF -> Ad-Valorem -> ISC -> IGV/IPM -> Perception -> Broker that mirrors
the Excel formulas (CCi VF 06.04.26).
"""

from decimal import Decimal

from engine.models import ImportRates, quantize_round
from engine.customs import compute_customs


# ── Helpers ───────────────────────────────────────────────────────────────

def _default_rates(**overrides) -> ImportRates:
    """Return default Peru rates with optional overrides."""
    kw = dict(
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
    kw.update(overrides)
    return ImportRates(**kw)


# ── Standard import with defaults ─────────────────────────────────────────

class TestStandardImport:
    """FOB=1000, Freight=200, default Peru rates (ISC=0%)."""

    def setup_method(self):
        self.result = compute_customs(
            fob=Decimal("1000"),
            freight=Decimal("200"),
            rates=_default_rates(),
        )

    def test_cfr(self):
        assert self.result.cfr == Decimal("1200")

    def test_insurance(self):
        # ROUND(1200 * 0.012, 2) = 14.40
        assert self.result.insurance == Decimal("14.40")

    def test_insurance_premium(self):
        # ROUND(14.40 * 0.015, 2) = 0.22
        assert self.result.insurance_premium == Decimal("0.22")

    def test_cif(self):
        # 1200 + 14.40 = 1214.40
        assert self.result.cif == Decimal("1214.40")

    def test_ad_valorem(self):
        # ROUND(1214.40 * 0.06, 0) = 73
        assert self.result.ad_valorem == Decimal("73")

    def test_isc_is_zero(self):
        # ROUND(1214.40 * 0, 0) = 0
        assert self.result.isc == Decimal("0")

    def test_igv(self):
        # base = 1214.40 + 73 + 0 = 1287.40
        # ROUND(1287.40 * 0.16, 0) = 206
        assert self.result.igv == Decimal("206")

    def test_ipm(self):
        # ROUND(1287.40 * 0.02, 0) = 26
        assert self.result.ipm == Decimal("26")

    def test_total_taxes(self):
        # 73 + 0 + 206 + 26 = 305
        assert self.result.total_taxes == Decimal("305")

    def test_perception(self):
        # ROUND((1214.40 + 305) * 0.035, 2) = ROUND(1519.40 * 0.035, 2) = 53.18
        assert self.result.igv_perception == Decimal("53.18")

    def test_broker_fee_uses_minimum(self):
        # broker_calc = ROUND(1214.40 * 0.01, 2) = 12.14
        # broker_min_usd = ROUND(100 / 3.72, 2) = 26.88
        # max(12.14, 26.88) = 26.88
        assert self.result.broker_fee == Decimal("26.88")

    def test_total_deuda_aduanera(self):
        # total_taxes + perception = 305 + 53.18 = 358.18
        assert self.result.total_deuda_aduanera == Decimal("358.18")

    def test_fob_and_freight_stored(self):
        assert self.result.fob == Decimal("1000")
        assert self.result.freight == Decimal("200")


# ── ISC cascading (10%) ───────────────────────────────────────────────────

class TestISCCascading:
    """Same base as standard, but isc_rate=0.10 -- ISC cascades into IGV/IPM."""

    def setup_method(self):
        self.result = compute_customs(
            fob=Decimal("1000"),
            freight=Decimal("200"),
            rates=_default_rates(isc_rate=Decimal("0.10")),
        )

    def test_cif_unchanged_by_isc_rate(self):
        """CIF is computed before ISC, so it must be the same as standard."""
        assert self.result.cif == Decimal("1214.40")

    def test_ad_valorem_unchanged(self):
        """Ad-Valorem is on CIF, not affected by ISC."""
        assert self.result.ad_valorem == Decimal("73")

    def test_isc(self):
        # ROUND(1214.40 * 0.10, 0) = 121
        assert self.result.isc == Decimal("121")

    def test_igv_includes_isc_in_base(self):
        # base = 1214.40 + 73 + 121 = 1408.40
        # ROUND(1408.40 * 0.16, 0) = 225
        assert self.result.igv == Decimal("225")

    def test_ipm_includes_isc_in_base(self):
        # ROUND(1408.40 * 0.02, 0) = 28
        assert self.result.ipm == Decimal("28")

    def test_total_taxes_with_isc(self):
        # 73 + 121 + 225 + 28 = 447
        assert self.result.total_taxes == Decimal("447")

    def test_perception_with_isc(self):
        # (1214.40 + 447) * 0.035 = 1661.40 * 0.035 = 58.149 -> 58.15
        assert self.result.igv_perception == Decimal("58.15")


# ── Broker commission exceeds minimum ─────────────────────────────────────

class TestBrokerExceedsMinimum:
    """FOB=50000: broker_calc should exceed broker_min_usd."""

    def setup_method(self):
        self.result = compute_customs(
            fob=Decimal("50000"),
            freight=Decimal("200"),
            rates=_default_rates(),
        )

    def test_cif(self):
        # CFR = 50200, insurance = ROUND(50200 * 0.012, 2) = 602.40
        # CIF = 50200 + 602.40 = 50802.40
        assert self.result.cif == Decimal("50802.40")

    def test_insurance(self):
        assert self.result.insurance == Decimal("602.40")

    def test_insurance_premium(self):
        # ROUND(602.40 * 0.015, 2) = 9.04
        assert self.result.insurance_premium == Decimal("9.04")

    def test_broker_fee_uses_calculated_value(self):
        # broker_calc = ROUND(50802.40 * 0.01, 2) = 508.02
        # broker_min_usd = 26.88
        # max(508.02, 26.88) = 508.02
        assert self.result.broker_fee == Decimal("508.02")

    def test_broker_fee_exceeds_minimum(self):
        broker_min = quantize_round(Decimal("100") / Decimal("3.72"), 2)
        assert self.result.broker_fee > broker_min

    def test_ad_valorem(self):
        # ROUND(50802.40 * 0.06, 0) = 3048
        assert self.result.ad_valorem == Decimal("3048")

    def test_igv(self):
        # base = 50802.40 + 3048 + 0 = 53850.40
        # ROUND(53850.40 * 0.16, 0) = 8616
        assert self.result.igv == Decimal("8616")

    def test_ipm(self):
        # ROUND(53850.40 * 0.02, 0) = 1077
        assert self.result.ipm == Decimal("1077")

    def test_total_taxes(self):
        # 3048 + 0 + 8616 + 1077 = 12741
        assert self.result.total_taxes == Decimal("12741")

    def test_perception(self):
        # (50802.40 + 12741) * 0.035 = 63543.40 * 0.035 = 2224.019 -> 2224.02
        assert self.result.igv_perception == Decimal("2224.02")

    def test_total_deuda(self):
        # 12741 + 2224.02 = 14965.02
        assert self.result.total_deuda_aduanera == Decimal("14965.02")


# ── Edge cases ────────────────────────────────────────────────────────────

class TestCustomsEdgeCases:

    def test_zero_fob_zero_freight(self):
        """All results should be zero when FOB and freight are both zero."""
        result = compute_customs(
            fob=Decimal("0"),
            freight=Decimal("0"),
            rates=_default_rates(),
        )
        assert result.cif == Decimal("0")
        assert result.total_taxes == Decimal("0")
        assert result.igv_perception == Decimal("0")
        # broker_fee should be the minimum (floor)
        broker_min = quantize_round(Decimal("100") / Decimal("3.72"), 2)
        assert result.broker_fee == broker_min

    def test_zero_freight(self):
        """Freight=0 means CFR == FOB."""
        result = compute_customs(
            fob=Decimal("5000"),
            freight=Decimal("0"),
            rates=_default_rates(),
        )
        assert result.cfr == Decimal("5000")
        assert result.freight == Decimal("0")

    def test_quantize_round_helper(self):
        """Verify our helper matches ROUND_HALF_UP behaviour."""
        assert quantize_round(Decimal("14.395"), 2) == Decimal("14.40")
        assert quantize_round(Decimal("14.385"), 2) == Decimal("14.39")
        assert quantize_round(Decimal("72.864"), 0) == Decimal("73")
        assert quantize_round(Decimal("72.5"), 0) == Decimal("73")
