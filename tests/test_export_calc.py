"""Tests for engine.export_calc -- export cost computation and allocation."""

from decimal import Decimal

from engine.models import SkuLine, ExportExpenseLine, quantize_round
from engine.export_calc import (
    compute_export_costs,
    allocate_export_costs,
    create_default_export_expenses,
)


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_lines() -> list[ExportExpenseLine]:
    """Build a set of export expense lines with known amounts.

    Logistics keys: transporte_interno(150), cargos_portuarios(100), embalaje(70)
    Documentation keys: documentacion(80)
    Other (uncategorised): agente_aduanas(50)

    Total logistics = 320, total documentation = 80, total all = 450
    """
    return [
        ExportExpenseLine(key="transporte_interno",
                          label="Transporte interno al puerto",
                          amount_usd=Decimal("150")),
        ExportExpenseLine(key="documentacion",
                          label="Documentacion y certificados",
                          amount_usd=Decimal("80")),
        ExportExpenseLine(key="cargos_portuarios",
                          label="Cargos portuarios / terminales",
                          amount_usd=Decimal("100")),
        ExportExpenseLine(key="agente_aduanas",
                          label="Agente de aduanas (exportacion)",
                          amount_usd=Decimal("50")),
        ExportExpenseLine(key="embalaje",
                          label="Embalaje y paletizacion",
                          amount_usd=Decimal("70")),
    ]


def _make_skus_60_40() -> list[SkuLine]:
    """Two SKUs already computed: A=60%, B=40%."""
    return [
        SkuLine(name="A", unit="kg", quantity=Decimal("60"),
                fob_unit_price=Decimal("10"),
                fob_total=Decimal("600"), proportion=Decimal("0.6")),
        SkuLine(name="B", unit="kg", quantity=Decimal("40"),
                fob_unit_price=Decimal("10"),
                fob_total=Decimal("400"), proportion=Decimal("0.4")),
    ]


# ── compute_export_costs ─────────────────────────────────────────────────

class TestComputeExportCosts:
    """FOB=1000, mixed expense lines."""

    def setup_method(self):
        self.result = compute_export_costs(
            fob_total=Decimal("1000"),
            lines=_make_lines(),
            num_skus=2,
        )

    def test_total_logistics(self):
        # transporte_interno(150) + cargos_portuarios(100) + embalaje(70) = 320
        assert self.result.total_logistics == Decimal("320")

    def test_total_documentation(self):
        # documentacion(80) = 80
        assert self.result.total_documentation == Decimal("80")

    def test_total_export_cost(self):
        # 150 + 80 + 100 + 50 + 70 = 450
        assert self.result.total_export_cost == Decimal("450")

    def test_fob_net(self):
        # 1000 - 450 = 550
        assert self.result.fob_net == Decimal("550")

    def test_fob_total_stored(self):
        assert self.result.fob_total == Decimal("1000")

    def test_num_skus_stored(self):
        assert self.result.num_skus == 2

    def test_lines_stored(self):
        assert len(self.result.lines) == 5


class TestExportCostsCategorisation:
    """Ensure keys are mapped to the right category."""

    def test_logistics_keys_counted(self):
        """All six logistics keys should contribute to total_logistics."""
        logistics_keys = [
            "transporte_interno", "cargos_portuarios", "embalaje",
            "seguro_interno", "almacenaje_puerto", "manipuleo_puerto",
        ]
        lines = [
            ExportExpenseLine(key=k, label=k, amount_usd=Decimal("10"))
            for k in logistics_keys
        ]
        result = compute_export_costs(Decimal("1000"), lines)
        assert result.total_logistics == Decimal("60")
        assert result.total_documentation == Decimal("0")

    def test_documentation_keys_counted(self):
        """All four documentation keys should contribute to total_documentation."""
        doc_keys = [
            "documentacion", "certificaciones", "visto_bueno",
            "gastos_bancarios",
        ]
        lines = [
            ExportExpenseLine(key=k, label=k, amount_usd=Decimal("25"))
            for k in doc_keys
        ]
        result = compute_export_costs(Decimal("1000"), lines)
        assert result.total_documentation == Decimal("100")
        assert result.total_logistics == Decimal("0")

    def test_other_keys_not_in_logistics_or_documentation(self):
        """agente_aduanas and otros_export go to total but not logistics/doc."""
        lines = [
            ExportExpenseLine(key="agente_aduanas", label="Agent",
                              amount_usd=Decimal("50")),
            ExportExpenseLine(key="otros_export", label="Otros",
                              amount_usd=Decimal("30")),
        ]
        result = compute_export_costs(Decimal("1000"), lines)
        assert result.total_logistics == Decimal("0")
        assert result.total_documentation == Decimal("0")
        assert result.total_export_cost == Decimal("80")


class TestExportCostsEdgeCases:

    def test_no_expenses(self):
        """No expense lines -> fob_net equals fob_total."""
        result = compute_export_costs(Decimal("5000"), [])
        assert result.fob_net == Decimal("5000")
        assert result.total_export_cost == Decimal("0")

    def test_default_expense_factory(self):
        """create_default_export_expenses returns 12 items, all zero."""
        lines = create_default_export_expenses()
        assert len(lines) == 12
        assert all(line.amount_usd == Decimal("0") for line in lines)


# ── allocate_export_costs ─────────────────────────────────────────────────

class TestAllocateExportCosts:
    """Proportional distribution of export costs to SKUs."""

    def setup_method(self):
        self.skus = _make_skus_60_40()
        export_result = compute_export_costs(
            fob_total=Decimal("1000"),
            lines=_make_lines(),
            num_skus=2,
        )
        self.allocs = allocate_export_costs(self.skus, export_result)

    def test_two_allocations_returned(self):
        assert len(self.allocs) == 2

    def test_sku_a_allocated_export_cost(self):
        # ROUND(450 * 0.6, 2) = 270.00
        assert self.allocs[0].allocated_export_cost == Decimal("270.00")

    def test_sku_b_allocated_export_cost(self):
        # ROUND(450 * 0.4, 2) = 180.00
        assert self.allocs[1].allocated_export_cost == Decimal("180.00")

    def test_sku_a_unit_export_cost(self):
        # ROUND(270 / 60, 4) = 4.5000
        assert self.allocs[0].unit_export_cost == Decimal("4.5000")

    def test_sku_b_unit_export_cost(self):
        # ROUND(180 / 40, 4) = 4.5000
        assert self.allocs[1].unit_export_cost == Decimal("4.5000")

    def test_sku_a_fob_net_per_unit(self):
        # ROUND((10*60 - 270) / 60, 4) = ROUND(330/60, 4) = 5.5000
        assert self.allocs[0].fob_net_per_unit == Decimal("5.5000")

    def test_sku_b_fob_net_per_unit(self):
        # ROUND((10*40 - 180) / 40, 4) = ROUND(220/40, 4) = 5.5000
        assert self.allocs[1].fob_net_per_unit == Decimal("5.5000")


class TestAllocateExportSingleSku:
    """Single SKU gets 100% of export costs."""

    def test_single_sku_full_allocation(self):
        skus = [
            SkuLine(name="Solo", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("20"),
                    fob_total=Decimal("2000"), proportion=Decimal("1")),
        ]
        export_result = compute_export_costs(
            fob_total=Decimal("2000"),
            lines=_make_lines(),
            num_skus=1,
        )
        allocs = allocate_export_costs(skus, export_result)

        assert len(allocs) == 1
        assert allocs[0].allocated_export_cost == Decimal("450.00")
        # ROUND(450 / 100, 4) = 4.5000
        assert allocs[0].unit_export_cost == Decimal("4.5000")
        # ROUND((20*100 - 450) / 100, 4) = ROUND(1550/100, 4) = 15.5000
        assert allocs[0].fob_net_per_unit == Decimal("15.5000")


class TestAllocateExportZeroQuantity:
    """Zero-quantity SKU receives zero export cost allocation."""

    def test_zero_qty_sku_gets_zero(self):
        skus = [
            SkuLine(name="Active", unit="pcs", quantity=Decimal("100"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("1000"), proportion=Decimal("1")),
            SkuLine(name="Ghost", unit="pcs", quantity=Decimal("0"),
                    fob_unit_price=Decimal("10"),
                    fob_total=Decimal("0"), proportion=Decimal("0")),
        ]
        export_result = compute_export_costs(
            fob_total=Decimal("1000"),
            lines=_make_lines(),
            num_skus=2,
        )
        allocs = allocate_export_costs(skus, export_result)

        ghost = allocs[1]
        assert ghost.allocated_export_cost == Decimal("0")
        assert ghost.unit_export_cost == Decimal("0")
        assert ghost.fob_net_per_unit == Decimal("0")
