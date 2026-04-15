"""Tab 3: Tributos Aduaneros - Calculo de CIF y tributos."""

import streamlit as st
import plotly.graph_objects as go
from decimal import Decimal
from engine.models import SkuLine, ImportRates, CustomsTaxResult, dec
from engine.customs import compute_customs
from engine.invoice import get_total_fob
from ui.components import (
    section_title, field_with_help, format_usd, cascade_value, display_tooltip,
)


def render(
    skus: list[SkuLine],
    rates: ImportRates,
    state_key: str = "customs",
) -> CustomsTaxResult | None:
    """Renderiza el tab de tributos aduaneros."""

    if not skus:
        st.warning("Completa el tab **Factura Comercial** primero.")
        return None

    total_fob = get_total_fob(skus)

    section_title("Tributos Aduaneros")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Calculo de tributos sobre el valor **CIF**. Ingresa el costo del flete internacional para completar la cascada.")
    with col_tt:
        display_tooltip("cif")

    # Freight input
    if state_key not in st.session_state:
        st.session_state[state_key] = {"freight": 0.0}

    freight_val = field_with_help(
        "Flete Internacional (USD)", "freight",
        value=st.session_state[state_key]["freight"],
        min_value=0.0, step=10.0, format_str="%.2f",
        key=f"{state_key}_freight",
    )
    st.session_state[state_key]["freight"] = freight_val

    # Compute
    result = compute_customs(
        fob=total_fob,
        freight=dec(freight_val),
        rates=rates,
    )

    st.divider()

    # Cascade display
    section_title("Cascada de Costos")

    col1, col2, col3 = st.columns(3)
    with col1:
        cascade_value("FOB", format_usd(result.fob))
        cascade_value("+ Flete", format_usd(result.freight))
        cascade_value("= CFR", format_usd(result.cfr))
    with col2:
        cascade_value("+ Seguro", format_usd(result.insurance))
        cascade_value("= CIF", format_usd(result.cif))
        cascade_value("Prima Seguro", format_usd(result.insurance_premium))
    with col3:
        cascade_value("Ad-Valorem", format_usd(result.ad_valorem))
        cascade_value("ISC", format_usd(result.isc))
        cascade_value("IGV (16%)", format_usd(result.igv))

    st.divider()

    col4, col5, col6 = st.columns(3)
    with col4:
        cascade_value("IPM (2%)", format_usd(result.ipm))
    with col5:
        cascade_value("Total Tributos", format_usd(result.total_taxes))
    with col6:
        cascade_value("Percepcion IGV", format_usd(result.igv_perception))

    col7, col8 = st.columns(2)
    with col7:
        cascade_value("Comision Agente de Aduanas", format_usd(result.broker_fee))
    with col8:
        cascade_value("Deuda Aduanera Total", format_usd(result.total_deuda_aduanera))

    # Waterfall chart
    st.divider()
    section_title("Composicion del Costo (Waterfall)")

    labels = ["FOB", "Flete", "Seguro", "Ad-Valorem", "ISC", "IGV", "IPM", "Percepcion", "Agente", "Total"]
    values = [
        float(result.fob),
        float(result.freight),
        float(result.insurance),
        float(result.ad_valorem),
        float(result.isc),
        float(result.igv),
        float(result.ipm),
        float(result.igv_perception),
        float(result.broker_fee),
        float(result.cif + result.total_taxes + result.igv_perception + result.broker_fee),
    ]
    measures = ["absolute"] + ["relative"] * 8 + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        textposition="outside",
        text=[f"${v:,.0f}" for v in values],
        connector={"line": {"color": "#d5c2a3"}},
        increasing={"marker": {"color": "#0a6a72"}},
        decreasing={"marker": {"color": "#a43b1a"}},
        totals={"marker": {"color": "#054f56"}},
    ))
    fig.update_layout(
        showlegend=False,
        height=400,
        margin=dict(t=30, b=30, l=40, r=20),
        yaxis_title="USD",
        font=dict(family="Outfit, sans-serif"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    return result
