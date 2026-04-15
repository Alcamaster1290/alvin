"""Tab 5: Costo por Producto - Prorrateo de costos a cada SKU."""

import streamlit as st
import pandas as pd
import plotly.express as px
from decimal import Decimal
from engine.models import SkuLine, CustomsTaxResult, ImportExpenses, SkuCostAllocation
from engine.allocation import allocate_costs
from ui.components import section_title, format_usd, display_tooltip


def render(
    skus: list[SkuLine],
    customs: CustomsTaxResult | None,
    expenses: ImportExpenses,
    exchange_rate: Decimal,
) -> list[SkuCostAllocation]:
    """Renderiza el tab de costo por producto."""

    if not skus or customs is None:
        st.warning("Completa los tabs anteriores primero: **Factura Comercial**, **Tributos** y **Gastos**.")
        return []

    section_title("Costo por Producto (Prorrateo)")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Los costos se distribuyen a cada SKU **proporcionalmente a su participacion FOB** sobre el total del embarque.")
    with col_tt:
        display_tooltip("fob")

    allocations = allocate_costs(skus, customs, expenses)

    # Main table
    table_data = []
    for a in allocations:
        pen_unit = a.unit_cost * exchange_rate
        table_data.append({
            "Producto": a.sku.name,
            "Unidad": a.sku.unit,
            "Cantidad": int(a.sku.quantity),
            "FOB Total (USD)": float(a.sku.fob_total),
            "Proporcion (%)": float(a.sku.proportion * 100),
            "CIF Asignado": float(a.allocated_cif),
            "Tributos Asignados": float(a.allocated_taxes),
            "Gastos Asignados": float(a.allocated_expenses),
            "Costo Total (USD)": float(a.total_cost),
            "Costo Unit. (USD)": float(a.unit_cost),
            "Costo Unit. (PEN)": float(pen_unit),
        })

    df = pd.DataFrame(table_data)

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "FOB Total (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Proporcion (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "CIF Asignado": st.column_config.NumberColumn(format="$%.2f"),
            "Tributos Asignados": st.column_config.NumberColumn(format="$%.2f"),
            "Gastos Asignados": st.column_config.NumberColumn(format="$%.2f"),
            "Costo Total (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Costo Unit. (USD)": st.column_config.NumberColumn(format="$%.4f"),
            "Costo Unit. (PEN)": st.column_config.NumberColumn(format="S/ %.4f"),
        },
    )

    # Summary metrics
    st.divider()
    total_cost = sum(a.total_cost for a in allocations)
    avg_unit = total_cost / sum(a.sku.quantity for a in allocations) if allocations else Decimal("0")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Costo Total Importacion", format_usd(total_cost))
    with col2:
        st.metric("Costo Unitario Promedio", format_usd(avg_unit))
    with col3:
        st.metric("Costo Prom. (PEN)", f"S/ {float(avg_unit * exchange_rate):,.4f}")

    # Horizontal bar chart: cost breakdown per SKU
    if len(allocations) > 1:
        st.divider()
        section_title("Desglose de Costo por SKU")

        chart_data = []
        for a in allocations:
            chart_data.append({"Producto": a.sku.name, "Componente": "CIF", "USD": float(a.allocated_cif)})
            chart_data.append({"Producto": a.sku.name, "Componente": "Tributos", "USD": float(a.allocated_taxes)})
            chart_data.append({"Producto": a.sku.name, "Componente": "Gastos", "USD": float(a.allocated_expenses)})

        chart_df = pd.DataFrame(chart_data)
        fig = px.bar(
            chart_df,
            x="USD", y="Producto",
            color="Componente",
            orientation="h",
            color_discrete_map={"CIF": "#0a6a72", "Tributos": "#705843", "Gastos": "#d5c2a3"},
            height=max(300, len(allocations) * 40),
        )
        fig.update_layout(
            font=dict(family="Outfit, sans-serif"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    return allocations
