"""Tab 8: Dashboard - KPIs y graficos resumen."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from decimal import Decimal
from engine.models import (
    SkuLine, CustomsTaxResult, ImportExpenses,
    SkuCostAllocation, SkuSellingPrice, ExportCostResult,
)
from ui.components import section_title, format_usd


def render(
    skus: list[SkuLine],
    customs: CustomsTaxResult | None,
    expenses: ImportExpenses,
    allocations: list[SkuCostAllocation],
    prices: list[SkuSellingPrice],
    export_result: ExportCostResult | None,
    exchange_rate: Decimal,
):
    """Renderiza el dashboard resumen."""

    section_title("Dashboard Resumen")

    col_info, _ = st.columns([10, 1])
    with col_info:
        st.markdown("Resumen ejecutivo de toda la operacion: **indicadores clave**, composicion de costos y analisis de rentabilidad.")

    if not skus or customs is None:
        st.warning("Completa los tabs anteriores primero: **Factura Comercial**, **Configuracion** y **Tributos**.")
        return

    total_fob = sum(s.fob_total for s in skus)
    total_cost = sum(a.total_cost for a in allocations)
    total_units = sum(s.quantity for s in skus)
    avg_unit_cost = total_cost / total_units if total_units > 0 else Decimal("0")

    # KPI row 1
    section_title("Indicadores Clave de Importacion")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total FOB", format_usd(total_fob))
    with c2:
        st.metric("Total CIF", format_usd(customs.cif))
    with c3:
        st.metric("Total Tributos", format_usd(customs.total_taxes))
    with c4:
        st.metric("Total Gastos", format_usd(expenses.total_expenses))
    with c5:
        st.metric("Costo Unit. Promedio", format_usd(avg_unit_cost))

    # KPI row 2
    if prices:
        total_profit = sum(
            p.profit_per_unit * dec_qty
            for p, a in zip(prices, allocations)
            if (dec_qty := a.sku.quantity) > 0
        )
        total_revenue = sum(
            p.retail_price_inc_igv * a.sku.quantity
            for p, a in zip(prices, allocations)
        )
        margin_pct = (total_profit / total_cost * 100) if total_cost > 0 else Decimal("0")

        c6, c7, c8, c9 = st.columns(4)
        with c6:
            st.metric("Ganancia Total", format_usd(total_profit))
        with c7:
            st.metric("Facturacion Total", format_usd(total_revenue))
        with c8:
            st.metric("Margen Ponderado", f"{float(margin_pct):.1f}%")
        with c9:
            st.metric("SKUs", str(len(skus)))

    # Export KPIs
    if export_result and export_result.total_export_cost > 0:
        st.divider()
        section_title("Indicadores de Exportacion")
        e1, e2, e3 = st.columns(3)
        with e1:
            st.metric("Gastos Exportacion", format_usd(export_result.total_export_cost))
        with e2:
            st.metric("FOB Neto", format_usd(export_result.fob_net))
        with e3:
            pct = (export_result.total_export_cost / export_result.fob_total * 100) if export_result.fob_total > 0 else Decimal("0")
            st.metric("Gastos / FOB", f"{float(pct):.2f}%")

    st.divider()

    # Charts row
    col_pie, col_bar = st.columns(2)

    # Pie chart: cost composition
    with col_pie:
        section_title("Composicion del Costo Total")
        pie_data = pd.DataFrame([
            {"Componente": "FOB", "USD": float(total_fob)},
            {"Componente": "Flete", "USD": float(customs.freight)},
            {"Componente": "Seguro", "USD": float(customs.insurance)},
            {"Componente": "Tributos", "USD": float(customs.total_taxes + customs.igv_perception)},
            {"Componente": "Gastos Logisticos", "USD": float(expenses.total_expenses)},
            {"Componente": "Agente Aduanas", "USD": float(customs.broker_fee)},
        ])
        pie_data = pie_data[pie_data["USD"] > 0]

        fig_pie = px.pie(
            pie_data,
            names="Componente", values="USD",
            color_discrete_sequence=["#0a6a72", "#054f56", "#705843",
                                     "#d5c2a3", "#2b1f15", "#a43b1a"],
            hole=0.4,
        )
        fig_pie.update_layout(
            font=dict(family="Outfit, sans-serif"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20, l=20, r=20),
            height=400,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Bar chart: top SKUs by unit cost
    with col_bar:
        section_title("Top SKUs por Costo Unitario")
        if allocations:
            sorted_allocs = sorted(allocations, key=lambda a: a.unit_cost, reverse=True)
            top_n = sorted_allocs[:15]
            bar_data = pd.DataFrame([
                {"Producto": a.sku.name, "Costo Unitario (USD)": float(a.unit_cost)}
                for a in top_n
            ])
            fig_bar = px.bar(
                bar_data,
                x="Costo Unitario (USD)", y="Producto",
                orientation="h",
                color_discrete_sequence=["#0a6a72"],
                height=400,
            )
            fig_bar.update_layout(
                font=dict(family="Outfit, sans-serif"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # Full waterfall: FOB to Final Price
    if prices:
        st.divider()
        section_title("De FOB a Precio Final (Promedio)")

        avg_fob_unit = total_fob / total_units if total_units > 0 else Decimal("0")
        avg_freight_unit = customs.freight / total_units if total_units > 0 else Decimal("0")
        avg_insurance_unit = customs.insurance / total_units if total_units > 0 else Decimal("0")
        avg_taxes_unit = customs.total_taxes / total_units if total_units > 0 else Decimal("0")
        avg_expenses_unit = expenses.total_expenses / total_units if total_units > 0 else Decimal("0")
        avg_profit_unit = sum(p.profit_per_unit for p in prices) / len(prices) if prices else Decimal("0")
        avg_igv_unit = sum(p.igv_on_price for p in prices) / len(prices) if prices else Decimal("0")

        labels = ["FOB Unit.", "+Flete", "+Seguro", "+Tributos", "+Gastos",
                  "= Costo", "+Margen", "+IGV", "Precio Final"]
        vals = [
            float(avg_fob_unit),
            float(avg_freight_unit),
            float(avg_insurance_unit),
            float(avg_taxes_unit),
            float(avg_expenses_unit),
            float(avg_unit_cost),
            float(avg_profit_unit),
            float(avg_igv_unit),
            float(avg_unit_cost + avg_profit_unit + avg_igv_unit),
        ]
        measures = ["absolute", "relative", "relative", "relative", "relative",
                    "total", "relative", "relative", "total"]

        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=vals,
            textposition="outside",
            text=[f"${v:,.2f}" for v in vals],
            connector={"line": {"color": "#d5c2a3"}},
            increasing={"marker": {"color": "#0a6a72"}},
            decreasing={"marker": {"color": "#a43b1a"}},
            totals={"marker": {"color": "#054f56"}},
        ))
        fig_wf.update_layout(
            showlegend=False,
            height=400,
            margin=dict(t=30, b=30, l=40, r=20),
            yaxis_title="USD por unidad",
            font=dict(family="Outfit, sans-serif"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_wf, use_container_width=True)
