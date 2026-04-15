"""Tests for engine.invoice -- FOB totals and SKU proportions."""

from decimal import Decimal

from engine.models import SkuLine
from engine.invoice import compute_invoice, get_total_fob


# ── Single SKU ────────────────────────────────────────────────────────────

def test_single_sku_fob_total():
    """100 units at $10 should produce fob_total=1000."""
    skus = [SkuLine(name="A", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"))]
    result = compute_invoice(skus)

    assert result[0].fob_total == Decimal("1000")


def test_single_sku_proportion_is_one():
    """A lone SKU must have proportion == 1."""
    skus = [SkuLine(name="A", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"))]
    compute_invoice(skus)

    assert skus[0].proportion == Decimal("1")


def test_single_sku_get_total_fob():
    """get_total_fob should equal the single SKU's fob_total after compute."""
    skus = [SkuLine(name="A", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"))]
    compute_invoice(skus)

    assert get_total_fob(skus) == Decimal("1000")


# ── Multi SKU ─────────────────────────────────────────────────────────────

def test_multi_sku_proportions_sum_to_one():
    """Proportions across all SKUs must sum to exactly 1."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("200"),
                fob_unit_price=Decimal("5")),   # fob=1000
        SkuLine(name="B", unit="pcs", quantity=Decimal("50"),
                fob_unit_price=Decimal("20")),   # fob=1000
    ]
    compute_invoice(skus)

    total_proportion = sum(s.proportion for s in skus)
    assert total_proportion == Decimal("1")


def test_multi_sku_individual_proportions():
    """Each SKU proportion should reflect its share of the total FOB."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("200"),
                fob_unit_price=Decimal("5")),   # fob=1000
        SkuLine(name="B", unit="pcs", quantity=Decimal("50"),
                fob_unit_price=Decimal("20")),   # fob=1000
    ]
    compute_invoice(skus)

    # Both contribute equally: 1000/2000 = 0.5
    assert skus[0].proportion == Decimal("0.5")
    assert skus[1].proportion == Decimal("0.5")


def test_multi_sku_unequal_proportions():
    """Verify unequal proportions: A=600, B=400 -> 0.6 and 0.4."""
    skus = [
        SkuLine(name="A", unit="kg", quantity=Decimal("60"),
                fob_unit_price=Decimal("10")),   # fob=600
        SkuLine(name="B", unit="kg", quantity=Decimal("40"),
                fob_unit_price=Decimal("10")),   # fob=400
    ]
    compute_invoice(skus)

    assert skus[0].proportion == Decimal("0.6")
    assert skus[1].proportion == Decimal("0.4")


def test_multi_sku_total_fob():
    """get_total_fob should sum all SKUs."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("200"),
                fob_unit_price=Decimal("5")),
        SkuLine(name="B", unit="pcs", quantity=Decimal("50"),
                fob_unit_price=Decimal("20")),
    ]
    compute_invoice(skus)

    assert get_total_fob(skus) == Decimal("2000")


# ── Zero quantity SKU ─────────────────────────────────────────────────────

def test_zero_quantity_sku_proportion_is_zero():
    """A SKU with quantity=0 should have proportion=0."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("100"),
                fob_unit_price=Decimal("10")),
        SkuLine(name="B", unit="pcs", quantity=Decimal("0"),
                fob_unit_price=Decimal("10")),
    ]
    compute_invoice(skus)

    assert skus[1].fob_total == Decimal("0")
    assert skus[1].proportion == Decimal("0")


def test_zero_quantity_sku_does_not_affect_other_proportions():
    """The non-zero SKU should carry 100% proportion when sibling is 0."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("100"),
                fob_unit_price=Decimal("10")),
        SkuLine(name="B", unit="pcs", quantity=Decimal("0"),
                fob_unit_price=Decimal("10")),
    ]
    compute_invoice(skus)

    assert skus[0].proportion == Decimal("1")


def test_all_zero_quantities():
    """If every SKU has zero quantity, all proportions should be 0."""
    skus = [
        SkuLine(name="A", unit="pcs", quantity=Decimal("0"),
                fob_unit_price=Decimal("10")),
        SkuLine(name="B", unit="pcs", quantity=Decimal("0"),
                fob_unit_price=Decimal("5")),
    ]
    compute_invoice(skus)

    assert skus[0].proportion == Decimal("0")
    assert skus[1].proportion == Decimal("0")
    assert get_total_fob(skus) == Decimal("0")
