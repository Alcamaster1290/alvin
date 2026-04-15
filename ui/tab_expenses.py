"""Tab 4: Gastos de Importacion - 21 items de gastos."""

import streamlit as st
import pandas as pd
from decimal import Decimal
from engine.models import ImportRates, ImportExpenses, dec
from engine.expenses import create_default_expenses, compute_expenses, ExpenseLine
from ui.components import section_title, format_usd, display_tooltip


def render(
    rates: ImportRates,
    state_key: str = "expenses",
) -> ImportExpenses:
    """Renderiza el tab de gastos de importacion."""

    defaults = create_default_expenses()

    if state_key not in st.session_state:
        st.session_state[state_key] = {
            line.key: 0.0 for line in defaults
        }

    section_title("Gastos de Importacion")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Ingresa los gastos operativos y logisticos de tu importacion en **USD**. Cada concepto tiene un icono **(?)** con detalles.")
    with col_tt:
        display_tooltip("handling")

    # Build editable form
    expense_lines: list[ExpenseLine] = []

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
                display_tooltip(template.key)

            expense_lines.append(ExpenseLine(
                key=template.key,
                label=template.label,
                amount_usd=dec(val),
            ))

    # Compute
    result = compute_expenses(expense_lines, rates.standard_igv)

    st.divider()

    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Subtotal Gastos", format_usd(result.subtotal_expenses))
    with col2:
        st.metric(f"IGV ({float(rates.standard_igv)*100:.0f}%) sobre Gastos", format_usd(result.igv_on_expenses))
    with col3:
        st.metric("Total Gastos (inc. IGV)", format_usd(result.total_expenses))

    # Detail expander
    with st.expander("Ver detalle de gastos", expanded=False):
        detail_data = []
        for line in expense_lines:
            if line.amount_usd > 0:
                detail_data.append({
                    "Concepto": line.label,
                    "Monto USD": float(line.amount_usd),
                })
        if detail_data:
            st.dataframe(
                pd.DataFrame(detail_data),
                use_container_width=True,
                column_config={
                    "Monto USD": st.column_config.NumberColumn(format="$%.2f"),
                },
            )
        else:
            st.info("No se han ingresado gastos.")

    return result
