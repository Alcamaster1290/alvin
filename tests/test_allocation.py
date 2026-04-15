"""Tests for engine.allocation -- proportional cost distribution to SKUs."""

from decimal import Decimal

from engine.models import (
    SkuLine,
    CustomsTaxResult,
    ImportExpenses,
    quantize_round,
)
from engine.allocation import allocate_costs


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_customs(
    cif=Decimal("1214.40"),
    total_taxes=Decimal("305"),
    igv_perception=Decimal("53.18"),
    broker_fee=Decimal("26.88"),
) -> CustomsTaxResult:
    """Build a CustomsTaxResult with the fields allocation cares about."""
    return CustomsTaxResult(
        cif=cif,
        total_taxes=total_taxes,
        igv_perception=igv_perception,
        broker_fee=broker_fee,
    )


def _make_expenses(total=Decimal("590")) -> ImportExpenses:
    """Build an ImportExpenses with the total that allocation uses."""
    return ImportExpenses(total_expenses=total)


# ── Two SKU 60/40 split ──────────────────────────────────────────────────

class TestTwoSkuSplit:
    """SKU A: 60% proportion, 60 units.  SKU B: 40% proportion, 40 units."""

    def setup_method(self):
        self.skus = [
            SkuLine(name="A", unit="kg", quantity=Decimal("60"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("600"), proportion=Decimal("0.6")),
            SkuLine(name="B", unit="kg", quantity=Decimal("40"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("400"), proportion=Decimal("0.4")),
        ]
        self.customs = _make_customs()
        self.expenses = _make_expenses()
        self.allocs = allocate_costs(self.skus, self.customs, self.expenses)

    def test_returns_two_allocations(self):
        assert len(self.allocs) == 2

    def test_sku_a_allocated_cif(self):
        # ROUND(1214.40 * 0.6, 2) = 728.64
        assert self.allocs[0].allocated_cif == Decimal("728.64")

    def test_sku_b_allocated_cif(self):
        # ROUND(1214.40 * 0.4, 2) = 485.76
        assert self.allocs[1].allocated_cif == Decimal("485.76")

    def test_sku_a_allocated_taxes(self):
        # (305 + 53.18 + 26.88) * 0.6 = 385.06 * 0.6 = 231.036 -> 231.04
        assert self.allocs[0].allocated_taxes == Decimal("231.04")

    def test_sku_b_allocated_taxes(self):
        # 385.06 * 0.4 = 154.024 -> 154.02
        assert self.allocs[1].allocated_taxes == Decimal("154.02")

    def test_sku_a_allocated_expenses(self):
        # ROUND(590 * 0.6, 2) = 354.00
        assert self.allocs[0].allocated_expenses == Decimal("354.00")

    def test_sku_b_allocated_expenses(self):
        # ROUND(590 * 0.4, 2) = 236.00
        assert self.allocs[1].allocated_expenses == Decimal("236.00")

    def test_sku_a_total_cost(self):
        # 728.64 + 231.04 + 354.00 = 1313.68
        assert self.allocs[0].total_cost == Decimal("1313.68")

    def test_sku_b_total_cost(self):
        # 485.76 + 154.02 + 236.00 = 875.78
        assert self.allocs[1].total_cost == Decimal("875.78")

    def test_sku_a_unit_cost(self):
        # ROUND(1313.68 / 60, 4) = 21.8947
        assert self.allocs[0].unit_cost == Decimal("21.8947")

    def test_sku_b_unit_cost(self):
        # ROUND(875.78 / 40, 4) = 21.8945
        assert self.allocs[1].unit_cost == Decimal("21.8945")

    def test_proportional_allocation_sums(self):
        """Sum of allocated CIF across SKUs should be close to total CIF."""
        total_alloc_cif = sum(a.allocated_cif for a in self.allocs)
        assert total_alloc_cif == Decimal("728.64") + Decimal("485.76")


# ── Single SKU gets 100% ─────────────────────────────────────────────────

class TestSingleSku:
    """A lone SKU with proportion=1 gets all costs."""

    def setup_method(self):
        self.skus = [
            SkuLine(name="Solo", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("1000"), proportion=Decimal("1")),
        ]
        self.customs = _make_customs()
        self.expenses = _make_expenses()
        self.allocs = allocate_costs(self.skus, self.customs, self.expenses)

    def test_single_alloc_returned(self):
        assert len(self.allocs) == 1

    def test_allocated_cif_equals_full_cif(self):
        assert self.allocs[0].allocated_cif == Decimal("1214.40")

    def test_allocated_taxes_equals_full_taxes(self):
        # (305 + 53.18 + 26.88) * 1 = 385.06
        assert self.allocs[0].allocated_taxes == Decimal("385.06")

    def test_allocated_expenses_equals_full_expenses(self):
        assert self.allocs[0].allocated_expenses == Decimal("590.00")

    def test_total_cost(self):
        # 1214.40 + 385.06 + 590.00 = 2189.46
        assert self.allocs[0].total_cost == Decimal("2189.46")

    def test_unit_cost(self):
        # ROUND(2189.46 / 100, 4) = 21.8946
        assert self.allocs[0].unit_cost == Decimal("21.8946")


# ── Zero-quantity SKU gets zero allocation ────────────────────────────────

class TestZeroQuantitySku:
    """A zero-quantity SKU should receive zero for all allocation fields."""

    def setup_method(self):
        self.skus = [
            SkuLine(name="Active", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("1000"), proportion=Decimal("1")),
            SkuLine(name="Empty", unit="pcs", quantity=Decimal("0"),
                    fob_unit_price=Decimal("5"),
                    fob_total=Decimal("0"), proportion=Decimal("0")),
        ]
        self.customs = _make_customs()
        self.expenses = _make_expenses()
        self.allocs = allocate_costs(self.skus, self.customs, self.expenses)

    def test_zero_sku_allocated_cif_is_zero(self):
        assert self.allocs[1].allocated_cif == Decimal("0")

    def test_zero_sku_allocated_taxes_is_zero(self):
        assert self.allocs[1].allocated_taxes == Decimal("0")

    def test_zero_sku_allocated_expenses_is_zero(self):
        assert self.allocs[1].allocated_expenses == Decimal("0")

    def test_zero_sku_total_cost_is_zero(self):
        assert self.allocs[1].total_cost == Decimal("0")

    def test_zero_sku_unit_cost_is_zero(self):
        assert self.allocs[1].unit_cost == Decimal("0")

    def test_active_sku_still_gets_full_allocation(self):
        assert self.allocs[0].total_cost == Decimal("2189.46")
