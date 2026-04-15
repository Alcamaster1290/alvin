"""Tab 2: Configuracion de tasas de importacion."""

import streamlit as st
from decimal import Decimal
from engine.models import ImportRates, dec
from engine.config import default_peru_rates
from ui.components import section_title, percentage_field, field_with_help, display_tooltip


def render(state_key: str = "config") -> ImportRates:
    """Renderiza el tab de configuracion de tasas."""

    defaults = default_peru_rates()

    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "ad_valorem": float(defaults.ad_valorem_rate * 100),
            "isc": float(defaults.isc_rate * 100),
            "igv": float(defaults.igv_rate * 100),
            "ipm": float(defaults.ipm_rate * 100),
            "insurance": float(defaults.insurance_rate * 100),
            "insurance_fee": float(defaults.insurance_fee_rate * 100),
            "broker": float(defaults.broker_commission_rate * 100),
            "broker_min": float(defaults.broker_min_usd),
            "perception": float(defaults.igv_perception_rate * 100),
            "exchange": float(defaults.exchange_rate),
        }

    section_title("Configuracion de Tasas y Parametros")

    col_info, col_tt = st.columns([10, 1])
    with col_info:
        st.markdown("Ajusta las tasas segun la **partida arancelaria** de tu producto y los parametros vigentes. Cada campo tiene un icono **(?)** con informacion detallada.")
    with col_tt:
        display_tooltip("ad_valorem")

    # Regulatory basis notice
    st.info(
        "**Supuestos regulatorios:** Tasas por defecto basadas en normativa peruana vigente "
        "(D.L. 1053, D.S. 010-2009-EF, D.S. 342-2016-EF, D.S. 055-99-EF, Ley 29173). "
        "Tipo de cambio: fuente SBS. Verificar vigencia antes de cada operacion.",
        icon="📋",
    )

    if st.button("Cargar valores por defecto Peru", key=f"{state_key}_defaults"):
        st.session_state[state_key] = {
            "ad_valorem": float(defaults.ad_valorem_rate * 100),
            "isc": float(defaults.isc_rate * 100),
            "igv": float(defaults.igv_rate * 100),
            "ipm": float(defaults.ipm_rate * 100),
            "insurance": float(defaults.insurance_rate * 100),
            "insurance_fee": float(defaults.insurance_fee_rate * 100),
            "broker": float(defaults.broker_commission_rate * 100),
            "broker_min": float(defaults.broker_min_usd),
            "perception": float(defaults.igv_perception_rate * 100),
            "exchange": float(defaults.exchange_rate),
        }
        st.rerun()

    col1, col2 = st.columns(2)

    with col1:
        section_title("Tributos Aduaneros")

        ad_valorem = percentage_field(
            "Ad-Valorem (%)", "ad_valorem",
            value=st.session_state[state_key]["ad_valorem"],
            key=f"{state_key}_ad_valorem",
        )
        st.session_state[state_key]["ad_valorem"] = ad_valorem

        isc = percentage_field(
            "ISC - Impuesto Selectivo al Consumo (%)", "isc",
            value=st.session_state[state_key]["isc"],
            key=f"{state_key}_isc",
        )
        st.session_state[state_key]["isc"] = isc

        igv = percentage_field(
            "IGV Aduanero (%)", "igv_aduanero",
            value=st.session_state[state_key]["igv"],
            key=f"{state_key}_igv",
        )
        st.session_state[state_key]["igv"] = igv

        ipm = percentage_field(
            "IPM - Imp. Promocion Municipal (%)", "ipm",
            value=st.session_state[state_key]["ipm"],
            key=f"{state_key}_ipm",
        )
        st.session_state[state_key]["ipm"] = ipm

        perception = percentage_field(
            "Percepcion del IGV (%)", "igv_perception",
            value=st.session_state[state_key]["perception"],
            key=f"{state_key}_perception",
        )
        st.session_state[state_key]["perception"] = perception

    with col2:
        section_title("Seguro y Agente de Aduanas")

        insurance = percentage_field(
            "Tasa de Seguro Internacional (%)", "insurance_rate",
            value=st.session_state[state_key]["insurance"],
            key=f"{state_key}_insurance",
        )
        st.session_state[state_key]["insurance"] = insurance

        insurance_fee = percentage_field(
            "Prima del Seguro (%)", "insurance_fee_rate",
            value=st.session_state[state_key]["insurance_fee"],
            key=f"{state_key}_insurance_fee",
        )
        st.session_state[state_key]["insurance_fee"] = insurance_fee

        broker = percentage_field(
            "Comision Agente de Aduanas (%)", "broker_commission_rate",
            value=st.session_state[state_key]["broker"],
            key=f"{state_key}_broker",
        )
        st.session_state[state_key]["broker"] = broker

        broker_min = field_with_help(
            "Minimo Comision Agente (USD)", "broker_fee",
            value=st.session_state[state_key]["broker_min"],
            min_value=0.0, step=10.0, format_str="%.2f",
            key=f"{state_key}_broker_min",
        )
        st.session_state[state_key]["broker_min"] = broker_min

        exchange = field_with_help(
            "Tipo de Cambio (USD/PEN)", "exchange_rate",
            value=st.session_state[state_key]["exchange"],
            min_value=0.01, step=0.01, format_str="%.4f",
            key=f"{state_key}_exchange",
        )
        st.session_state[state_key]["exchange"] = exchange

    # Build ImportRates from state
    s = st.session_state[state_key]
    return ImportRates(
        ad_valorem_rate=dec(s["ad_valorem"]) / dec(100),
        isc_rate=dec(s["isc"]) / dec(100),
        igv_rate=dec(s["igv"]) / dec(100),
        ipm_rate=dec(s["ipm"]) / dec(100),
        insurance_rate=dec(s["insurance"]) / dec(100),
        insurance_fee_rate=dec(s["insurance_fee"]) / dec(100),
        broker_commission_rate=dec(s["broker"]) / dec(100),
        broker_min_usd=dec(s["broker_min"]),
        igv_perception_rate=dec(s["perception"]) / dec(100),
        exchange_rate=dec(s["exchange"]),
    )
