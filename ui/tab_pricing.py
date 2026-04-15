"""Tab 6: Precio de Venta - Calculo de precio con margen."""

import streamlit as st
import pandas as pd
import plotly.express as px
from decimal import Decimal
from engine.models import SkuCostAllocation, SkuSellingPrice, dec
from engine.pricing import compute_selling_prices
from ui.components import section_title, format_usd, display_tooltip


def render(
    allocations: list[SkuCostAllocation],
    exchange_rate: Decimal,
    state_key: str = "pricing",
) -> list[SkuSellingPrice]:
    """Renderiza el tab de precio de venta."""

    if not allocations:
        st.warning("Completa los tabs anteriores primero: **Factura Comercial**, **Tributos**, **Gastos** y **Costo por Producto**.")
        return []

    section_title("Precio de Venta")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Define el **margen de ganancia sobre el precio de venta** para cada producto. Formula: `Precio = Costo / (1 - Margen%)`. El precio final incluye el **IGV (18%)**.")
    with col_tt:
        display_tooltip("margin")

    # Margin config
    if state_key not in st.session_state:
        st.session_state[state_key] = {"default_margin": 40.0, "margins": {}}

    col_default, _ = st.columns([4, 8])
    with col_default:
        default_margin = st.number_input(
            "Margen sobre precio de venta (%)",
            value=st.session_state[state_key]["default_margin"],
            min_value=0.0,
            max_value=99.0,
            step=1.0,
            format="%.1f",
            key=f"{state_key}_default_margin",
        )
        st.session_state[state_key]["default_margin"] = default_margin

    # Per-SKU margin editor
    with st.expander("Personalizar margen por producto", expanded=False):
        margin_data = []
        for alloc in allocations:
            stored = st.session_state[state_key]["margins"].get(alloc.sku.name)
            margin_data.append({
                "Producto": alloc.sku.name,
                "Margen (%)": stored if stored is not None else default_margin,
            })
        margin_df = pd.DataFrame(margin_data)
        edited_margins = st.data_editor(
            margin_df,
            use_container_width=True,
            key=f"{state_key}_margin_editor",
            column_config={
                "Producto": st.column_config.TextColumn(disabled=True),
                "Margen (%)": st.column_config.NumberColumn(
                    min_value=0.0, max_value=99.0, format="%.1f"
                ),
            },
        )
        for _, row in edited_margins.iterrows():
            st.session_state[state_key]["margins"][row["Producto"]] = row["Margen (%)"]

    # Build margins dict
    margins_dec: dict[str, Decimal] = {}
    for alloc in allocations:
        m = st.session_state[state_key]["margins"].get(alloc.sku.name, default_margin)
        margins_dec[alloc.sku.name] = dec(m) / dec(100)

    # Compute
    prices = compute_selling_prices(
        allocations,
        margins=margins_dec,
        default_margin=dec(default_margin) / dec(100),
    )

    # Results table
    st.divider()
    section_title("Tabla de Precios de Venta")

    table_data = []
    for p in prices:
        table_data.append({
            "Producto": p.sku_name,
            "Costo Unit. (USD)": float(p.unit_cost),
            "Margen (%)": float(p.margin_percent * 100),
            "Precio sin IGV (USD)": float(p.retail_price_ex_igv),
            "IGV (18%)": float(p.igv_on_price),
            "Precio Final (USD)": float(p.retail_price_inc_igv),
            "Precio Final (PEN)": float(p.retail_price_inc_igv * exchange_rate),
            "Ganancia Unit. (USD)": float(p.profit_per_unit),
        })

    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        column_config={
            "Costo Unit. (USD)": st.column_config.NumberColumn(format="$%.4f"),
            "Margen (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Precio sin IGV (USD)": st.column_config.NumberColumn(format="$%.4f"),
            "IGV (18%)": st.column_config.NumberColumn(format="$%.4f"),
            "Precio Final (USD)": st.column_config.NumberColumn(format="$%.4f"),
            "Precio Final (PEN)": st.column_config.NumberColumn(format="S/ %.4f"),
            "Ganancia Unit. (USD)": st.column_config.NumberColumn(format="$%.4f"),
        },
    )

    # Profit summary
    st.divider()
    total_profit = sum(p.profit_per_unit * dec(a.sku.quantity) for p, a in zip(prices, allocations))
    total_revenue = sum(p.retail_price_inc_igv * dec(a.sku.quantity) for p, a in zip(prices, allocations))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ganancia Total Estimada", format_usd(total_profit))
    with col2:
        st.metric("Facturacion Total (inc. IGV)", format_usd(total_revenue))
    with col3:
        avg_margin = (total_profit / sum(a.total_cost for a in allocations) * 100) if allocations else Decimal("0")
        st.metric("Margen Ponderado (%)", f"{float(avg_margin):.1f}%")

    # Profit chart
    if len(prices) > 1:
        chart_data = []
        for p, a in zip(prices, allocations):
            chart_data.append({
                "Producto": p.sku_name,
                "Componente": "Costo",
                "USD": float(p.unit_cost),
            })
            chart_data.append({
                "Producto": p.sku_name,
                "Componente": "Ganancia",
                "USD": float(p.profit_per_unit),
            })
            chart_data.append({
                "Producto": p.sku_name,
                "Componente": "IGV",
                "USD": float(p.igv_on_price),
            })

        fig = px.bar(
            pd.DataFrame(chart_data),
            x="Producto", y="USD",
            color="Componente",
            color_discrete_map={"Costo": "#705843", "Ganancia": "#0a6a72", "IGV": "#d5c2a3"},
            barmode="stack",
            height=400,
        )
        fig.update_layout(
            font=dict(family="Outfit, sans-serif"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    return prices
