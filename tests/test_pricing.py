"""Tests for engine.pricing -- selling price with margin-on-price formula.

Critical formula: Price = Cost / (1 - Margin%)
The margin is a percentage of the selling price, NOT of cost.
"""

from decimal import Decimal

from engine.models import SkuLine, SkuCostAllocation, quantize_round
from engine.pricing import compute_selling_prices


# ── Helpers ───────────────────────────────────────────────────────────────

def _alloc(name: str, unit_cost: Decimal, quantity: Decimal = Decimal("100")) -> SkuCostAllocation:
    """Convenience builder for a SkuCostAllocation with a given unit cost."""
    sku = SkuLine(name=name, unit="pcs", quantity=quantity,
                  fob_unit_price=Decimal("0"))
    return SkuCostAllocation(sku=sku, unit_cost=unit_cost)


# ── Standard 40% margin ──────────────────────────────────────────────────

class TestStandardMargin:
    """cost=10, margin=40% -> price_ex_igv = 10 / (1 - 0.4) = 16.6667."""

    def setup_method(self):
        allocs = [_alloc("Widget", Decimal("10"))]
        results = compute_selling_prices(
            allocs,
            default_margin=Decimal("0.40"),
            igv_rate=Decimal("0.18"),
        )
        self.price = results[0]

    def test_retail_price_ex_igv(self):
        # 10 / 0.60 = 16.66666... -> quantize_round(_, 4) = 16.6667
        assert self.price.retail_price_ex_igv == Decimal("16.6667")

    def test_igv_on_price(self):
        # ROUND(16.6667 * 0.18, 4) = 3.0000
        assert self.price.igv_on_price == Decimal("3.0000")

    def test_retail_price_inc_igv(self):
        # 16.6667 + 3.0000 = 19.6667
        assert self.price.retail_price_inc_igv == Decimal("19.6667")

    def test_profit_per_unit(self):
        # 16.6667 - 10 = 6.6667
        assert self.price.profit_per_unit == Decimal("6.6667")

    def test_profit_is_40_percent_of_price(self):
        """The margin should be ~40% of the ex-IGV price."""
        ratio = self.price.profit_per_unit / self.price.retail_price_ex_igv
        # Due to rounding, check within tolerance
        assert abs(ratio - Decimal("0.40")) < Decimal("0.001")

    def test_margin_stored(self):
        assert self.price.margin_percent == Decimal("0.40")

    def test_unit_cost_stored(self):
        assert self.price.unit_cost == Decimal("10")


# ── Zero margin ───────────────────────────────────────────────────────────

class TestZeroMargin:
    """margin=0% -> price = cost exactly."""

    def setup_method(self):
        allocs = [_alloc("BasicItem", Decimal("10"))]
        results = compute_selling_prices(
            allocs,
            default_margin=Decimal("0"),
            igv_rate=Decimal("0.18"),
        )
        self.price = results[0]

    def test_price_equals_cost(self):
        assert self.price.retail_price_ex_igv == Decimal("10.0000")

    def test_profit_is_zero(self):
        assert self.price.profit_per_unit == Decimal("0.0000")

    def test_igv_on_cost(self):
        # ROUND(10 * 0.18, 4) = 1.8000
        assert self.price.igv_on_price == Decimal("1.8000")

    def test_retail_inc_igv(self):
        assert self.price.retail_price_inc_igv == Decimal("11.8000")


# ── Custom margin per SKU ─────────────────────────────────────────────────

class TestCustomMarginPerSku:
    """Different SKUs can have individually assigned margins."""

    def setup_method(self):
        allocs = [
            _alloc("Premium", Decimal("10")),
            _alloc("Budget", Decimal("10")),
        ]
        margins = {
            "Premium": Decimal("0.50"),
            "Budget": Decimal("0.20"),
        }
        self.results = compute_selling_prices(
            allocs,
            margins=margins,
            default_margin=Decimal("0.30"),
            igv_rate=Decimal("0.18"),
        )

    def test_premium_uses_50_percent_margin(self):
        # 10 / (1 - 0.50) = 20.0000
        assert self.results[0].retail_price_ex_igv == Decimal("20.0000")
        assert self.results[0].margin_percent == Decimal("0.50")

    def test_budget_uses_20_percent_margin(self):
        # 10 / (1 - 0.20) = 12.5000
        assert self.results[1].retail_price_ex_igv == Decimal("12.5000")
        assert self.results[1].margin_percent == Decimal("0.20")

    def test_premium_profit(self):
        # 20.0000 - 10 = 10.0000
        assert self.results[0].profit_per_unit == Decimal("10.0000")

    def test_budget_profit(self):
        # 12.5000 - 10 = 2.5000
        assert self.results[1].profit_per_unit == Decimal("2.5000")

    def test_premium_igv(self):
        # ROUND(20.0000 * 0.18, 4) = 3.6000
        assert self.results[0].igv_on_price == Decimal("3.6000")

    def test_budget_igv(self):
        # ROUND(12.5000 * 0.18, 4) = 2.2500
        assert self.results[1].igv_on_price == Decimal("2.2500")


class TestDefaultMarginFallback:
    """SKUs not in the margins dict use the default_margin."""

    def test_unlisted_sku_uses_default(self):
        allocs = [_alloc("Unlisted", Decimal("10"))]
        margins = {"OtherSku": Decimal("0.50")}
        results = compute_selling_prices(
            allocs,
            margins=margins,
            default_margin=Decimal("0.30"),
        )
        # 10 / (1 - 0.30) = 14.2857
        assert results[0].retail_price_ex_igv == Decimal("14.2857")
        assert results[0].margin_percent == Decimal("0.30")


class TestMarginEdgeCases:

    def test_margin_100_percent_returns_zero(self):
        """Margin of 100% would cause division by zero; code returns 0."""
        allocs = [_alloc("Impossible", Decimal("10"))]
        results = compute_selling_prices(
            allocs,
            default_margin=Decimal("1.0"),
        )
        assert results[0].retail_price_ex_igv == Decimal("0")

    def test_zero_cost_zero_margin(self):
        """Zero cost should produce zero price regardless of margin."""
        allocs = [_alloc("Free", Decimal("0"))]
        results = compute_selling_prices(
            allocs,
            default_margin=Decimal("0.40"),
        )
        assert results[0].retail_price_ex_igv == Decimal("0.0000")
        assert results[0].profit_per_unit == Decimal("0.0000")
