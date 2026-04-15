"""
Expediente de Costos de Importacion / Exportacion
ADEX - Data Trade

Entry point: streamlit run import_cost_calculator/app.py
"""

import sys
from pathlib import Path

# Ensure package imports work regardless of launch directory
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
_PROJECT_DIR = _APP_DIR.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

import streamlit as st
from decimal import Decimal

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Expediente de Costos - ADEX Data Trade",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.theme import inject_theme, render_header
from ui.tab_invoice import render as render_invoice
from ui.tab_config import render as render_config
from ui.tab_customs import render as render_customs
from ui.tab_expenses import render as render_expenses
from ui.tab_allocation import render as render_allocation
from ui.tab_pricing import render as render_pricing
from ui.tab_export_costs import render as render_export
from ui.tab_dashboard import render as render_dashboard
from export.to_excel import generate_excel
from engine.models import ImportExpenses
from engine.contracts import export_trade_costs


def main():
    inject_theme()
    render_header()

    # Sidebar
    with st.sidebar:
        # Toggle para colapsar contenido del sidebar
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] [data-testid="stMarkdown"] {
                font-size: 0.92rem;
            }
            .sidebar-toggle { cursor: pointer; user-select: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        sidebar_expanded = st.toggle("Mostrar panel lateral", value=True, key="sidebar_toggle")

        if sidebar_expanded:
            st.markdown("#### Ecosistema ADEX")

            sislope_url = "https://sis-lo-pe.vercel.app"
            st.link_button(
                "SisLoPe - Sistema Logistico del Peru",
                sislope_url,
                use_container_width=True,
            )

            palletizer_url = "https://adex-palletizer.vercel.app"
            st.link_button(
                "Pallet Solver - Paletizacion 3D",
                palletizer_url,
                use_container_width=True,
            )

            st.markdown("---")

            with st.expander("Acerca de este expediente", expanded=True):
                st.markdown(
                    """
**Expediente de Costos de Importacion y Exportacion**

Herramienta de calculo tecnico de costos aterrizados para
operaciones de comercio exterior en Peru, basada en las plantillas
CCi desarrolladas por profesionales del sector.

**Flujo del expediente (Importacion):**
1. Factura Comercial (FOB por SKU)
2. Configuracion de tasas arancelarias
3. Tributos aduaneros (CIF, Ad-Valorem, ISC, IGV, IPM)
4. Gastos de importacion (21 conceptos)
5. Prorrateo de costos por producto
6. Precio de venta con margen

**Precision financiera:**
Aritmetica `decimal.Decimal` con redondeo `ROUND_HALF_UP`,
replicando exactamente las funciones `ROUND()` de Excel.

**Capacidad:** Hasta 500 SKUs por operacion.

**Normativa de referencia:**
- Ley General de Aduanas (D.L. 1053)
- Reglamento de la Ley General de Aduanas (D.S. 010-2009-EF)
- Arancel de Aduanas (D.S. 342-2016-EF y modificatorias)
- TUO de la Ley del IGV e ISC (D.S. 055-99-EF)
- Regimen de Percepciones del IGV (Ley 29173)

**Fuentes de tasas:**
- SUNAT ([sunat.gob.pe](https://www.sunat.gob.pe))
- SBS - Tipo de cambio ([sbs.gob.pe](https://www.sbs.gob.pe))
- Arancel Nacional de Aduanas

**Integraciones:**
- Importar caso desde ADEX Palletizer (trade-case.v1)
- Exportar expediente completo (trade-costs.v1 o Excel)
                    """
                )

            with st.expander("Formulas clave"):
                st.markdown(
                    """
| Concepto | Formula |
|----------|---------|
| CIF | FOB + Flete + Seguro |
| Ad-Valorem | ROUND(CIF x tasa, 0) |
| ISC | ROUND(CIF x tasa, 0) |
| IGV (16%) | ROUND((CIF+AdVal+ISC) x 0.16, 0) |
| IPM (2%) | ROUND((CIF+AdVal+ISC) x 0.02, 0) |
| Percepcion | ROUND((CIF+Tributos) x tasa, 2) |
| Agente | MAX(CIF x %, min USD) |
| Prorrateo | Costo x (FOB_sku / FOB_total) |
| Precio | Costo / (1 - Margen%) |
                    """
                )

            st.markdown("---")

        st.caption("ADEX Data Trade v1.0 | by Alvaro Caceres")

    # Main tabs
    tabs = st.tabs([
        "📋 Factura Comercial",
        "⚙️ Configuracion",
        "🏛️ Tributos Aduaneros",
        "📦 Gastos Importacion",
        "💰 Costo por Producto",
        "🏷️ Precio de Venta",
        "🚢 Costos Exportacion",
        "📊 Dashboard",
    ])

    # Tab 1: Invoice
    with tabs[0]:
        skus = render_invoice()

    # Tab 2: Config
    with tabs[1]:
        rates = render_config()

    # Tab 3: Customs
    with tabs[2]:
        customs = render_customs(skus, rates)

    # Tab 4: Expenses
    with tabs[3]:
        expenses = render_expenses(rates)

    # Tab 5: Allocation
    with tabs[4]:
        allocations = render_allocation(
            skus, customs, expenses, rates.exchange_rate
        )

    # Tab 6: Pricing
    with tabs[5]:
        prices = render_pricing(allocations, rates.exchange_rate)

    # Tab 7: Export Costs
    with tabs[6]:
        export_result, export_allocations = render_export(skus, rates.exchange_rate)

    # Tab 8: Dashboard
    with tabs[7]:
        render_dashboard(
            skus, customs, expenses, allocations, prices,
            export_result, rates.exchange_rate,
        )

        # Export buttons in dashboard
        if skus and customs:
            st.divider()
            from ui.components import section_title as _st
            _st("Exportar Expediente")

            col_excel, col_json = st.columns(2)

            with col_excel:
                excel_bytes = generate_excel(
                    skus=skus,
                    rates=rates,
                    customs=customs,
                    expenses=expenses,
                    allocations=allocations,
                    prices=prices,
                    export_result=export_result,
                    exchange_rate=rates.exchange_rate,
                )

                st.download_button(
                    label="Descargar Excel Completo",
                    data=excel_bytes,
                    file_name="expediente_costos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with col_json:
                import json as _json
                case_id = st.session_state.get("trade_case_id")
                costs_dict = export_trade_costs(
                    case_id=case_id,
                    rates=rates,
                    customs=customs,
                    expenses=expenses,
                    allocations=allocations,
                    prices=prices,
                    export_result=export_result,
                    export_allocations=export_allocations,
                    exchange_rate=rates.exchange_rate,
                )
                costs_json = _json.dumps(costs_dict, indent=2, ensure_ascii=False)

                st.download_button(
                    label="Descargar trade-costs.v1 (JSON)",
                    data=costs_json,
                    file_name=f"trade-costs-{costs_dict['caseId'][:8]}.json",
                    mime="application/json",
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
