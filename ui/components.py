"""Componentes reutilizables de UI con soporte de tooltips (?)."""

import streamlit as st
from decimal import Decimal
from ui.tooltips import get_tooltip


def field_with_help(
    label: str,
    tooltip_key: str,
    *,
    value: float = 0.0,
    min_value: float | None = None,
    max_value: float | None = None,
    step: float | None = None,
    format_str: str | None = None,
    key: str | None = None,
    disabled: bool = False,
) -> float:
    """Renderiza un number_input con un icono (?) informativo al costado."""
    help_text = get_tooltip(tooltip_key)
    col1, col2 = st.columns([10, 1])
    with col1:
        kwargs = {"label": label, "value": value, "key": key, "disabled": disabled}
        if min_value is not None:
            kwargs["min_value"] = min_value
        if max_value is not None:
            kwargs["max_value"] = max_value
        if step is not None:
            kwargs["step"] = step
        if format_str is not None:
            kwargs["format"] = format_str
        result = st.number_input(**kwargs)
    with col2:
        if help_text:
            with st.popover("?"):
                st.markdown(help_text)
        else:
            st.write("")
    return result


def percentage_field(
    label: str,
    tooltip_key: str,
    *,
    value: float = 0.0,
    key: str | None = None,
) -> float:
    """Campo de porcentaje (0-100) con tooltip."""
    return field_with_help(
        label,
        tooltip_key,
        value=value,
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        format_str="%.2f",
        key=key,
    )


def usd_field(
    label: str,
    tooltip_key: str,
    *,
    value: float = 0.0,
    key: str | None = None,
) -> float:
    """Campo de monto en USD con tooltip."""
    return field_with_help(
        label,
        tooltip_key,
        value=value,
        min_value=0.0,
        step=0.01,
        format_str="%.2f",
        key=key,
    )


def display_tooltip(tooltip_key: str):
    """Muestra solo el icono (?) con el tooltip, sin campo de entrada."""
    help_text = get_tooltip(tooltip_key)
    if help_text:
        with st.popover("?"):
            st.markdown(help_text)


def metric_card(label: str, value: str, tooltip_key: str = ""):
    """Muestra una metrica con tooltip opcional."""
    col1, col2 = st.columns([10, 1])
    with col1:
        st.metric(label=label, value=value)
    with col2:
        if tooltip_key:
            display_tooltip(tooltip_key)


def section_title(text: str):
    """Renderiza un titulo de seccion estilizado."""
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def cascade_value(label: str, value: str):
    """Renderiza un valor en formato de cascada (para tributos)."""
    st.markdown(
        f"""
        <div class="cascade-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_usd(value: Decimal) -> str:
    """Formatea un valor Decimal como USD."""
    return f"USD {value:,.2f}"


def format_pen(value: Decimal, exchange_rate: Decimal) -> str:
    """Formatea un valor Decimal como PEN."""
    pen = value * exchange_rate
    return f"S/ {pen:,.2f}"


def format_pct(value: Decimal) -> str:
    """Formatea un valor Decimal como porcentaje."""
    return f"{value * 100:.2f}%"
