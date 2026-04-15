"""Tab 7: Costos de Exportacion."""

import streamlit as st
import pandas as pd
import plotly.express as px
from decimal import Decimal
from engine.models import SkuLine, ExportCostResult, SkuExportAllocation, dec
from engine.export_calc import (
    create_default_export_expenses,
    compute_export_costs,
    allocate_export_costs,
    ExportExpenseLine,
)
from engine.invoice import get_total_fob
from ui.components import section_title, format_usd, display_tooltip


def render(
    skus: list[SkuLine],
    exchange_rate: Decimal,
    state_key: str = "export_costs",
) -> tuple[ExportCostResult | None, list[SkuExportAllocation]]:
    """Renderiza el tab de costos de exportacion."""

    if not skus:
        st.warning("Completa el tab **Factura Comercial** primero.")
        return None, []

    total_fob = get_total_fob(skus)
    defaults = create_default_export_expenses()

    if state_key not in st.session_state:
        st.session_state[state_key] = {
            line.key: 0.0 for line in defaults
        }

    section_title("Costos de Exportacion")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Ingresa los costos asociados a la exportacion de tu mercancia. Estos gastos se restan del FOB para obtener el **FOB neto**.")
    with col_tt:
        display_tooltip("export_transporte_interno")

    # Build editable form
    export_lines: list[ExportExpenseLine] = []
    col_left, col_right = st.columns(2)
    half = len(defaults) // 2 + 1

    for idx, template in enumerate(defaults):
        container = col_left if idx < half else col_right
        with container:
            col_label, col_input, col_help = st.columns([5, 4, 1])
            with col_label:
                st.markdown(f"**{template.label}**")
            with col_input:
                val = st.number_input(
                    template.label,
                    value=st.session_state[state_key].get(template.key, 0.0),
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"{state_key}_{template.key}",
                    label_visibility="collapsed",
                )
                st.session_state[state_key][template.key] = val
            with col_help:
                display_tooltip(f"export_{template.key}")

            export_lines.append(ExportExpenseLine(
                key=template.key,
                label=template.label,
                amount_usd=dec(val),
            ))

    # Compute
    result = compute_export_costs(total_fob, export_lines, len(skus))
    allocations = allocate_export_costs(skus, result)

    st.divider()

    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("FOB Bruto", format_usd(result.fob_total))
    with col2:
        st.metric("Gastos Logisticos", format_usd(result.total_logistics))
    with col3:
        st.metric("Gastos Documentacion", format_usd(result.total_documentation))

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Total Gastos Export.", format_usd(result.total_export_cost))
    with col5:
        st.metric("FOB Neto", format_usd(result.fob_net))
    with col6:
        pct = (result.total_export_cost / result.fob_total * 100) if result.fob_total > 0 else Decimal("0")
        st.metric("Gastos como % del FOB", f"{float(pct):.2f}%")

    # Per-SKU allocation table
    if allocations:
        st.divider()
        section_title("Costo de Exportacion por Producto")

        table_data = []
        for a in allocations:
            table_data.append({
                "Producto": a.sku.name,
                "Cantidad": int(a.sku.quantity),
                "FOB Total": float(a.sku.fob_total),
                "Gasto Export. Asignado": float(a.allocated_export_cost),
                "Costo Export. Unit.": float(a.unit_export_cost),
                "FOB Neto Unit.": float(a.fob_net_per_unit),
                "FOB Neto Unit. (PEN)": float(a.fob_net_per_unit * exchange_rate),
            })

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            column_config={
                "FOB Total": st.column_config.NumberColumn(format="$%.2f"),
                "Gasto Export. Asignado": st.column_config.NumberColumn(format="$%.2f"),
                "Costo Export. Unit.": st.column_config.NumberColumn(format="$%.4f"),
                "FOB Neto Unit.": st.column_config.NumberColumn(format="$%.4f"),
                "FOB Neto Unit. (PEN)": st.column_config.NumberColumn(format="S/ %.4f"),
            },
        )

    # Pie chart of export costs
    cost_items = [
        {"Concepto": line.label, "USD": float(line.amount_usd)}
        for line in export_lines if line.amount_usd > 0
    ]
    if cost_items:
        st.divider()
        section_title("Distribucion de Gastos de Exportacion")
        fig = px.pie(
            pd.DataFrame(cost_items),
            names="Concepto", values="USD",
            color_discrete_sequence=["#0a6a72", "#054f56", "#705843", "#d5c2a3",
                                     "#2b1f15", "#a43b1a", "#1c6d3a", "#7f5a12",
                                     "#d9eff1", "#f4efe6", "#ecddc5", "#b6e3c8"],
            height=400,
        )
        fig.update_layout(
            font=dict(family="Outfit, sans-serif"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    return result, allocations
