"""Tema CSS inyectado que replica la paleta visual de adex-palletizer."""

ADEX_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap');

/* --- Global --- */
[data-testid="stAppViewContainer"] {
    font-family: 'Outfit', 'Segoe UI', sans-serif;
}

.main .block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
}

/* --- Header --- */
.app-header {
    background: linear-gradient(135deg, #0a6a72 0%, #054f56 100%);
    color: white;
    padding: 1.2rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px rgba(10, 106, 114, 0.25);
}
.app-header h1 {
    margin: 0;
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 1.6rem;
    letter-spacing: -0.02em;
}
.app-header p {
    margin: 0.2rem 0 0;
    opacity: 0.85;
    font-size: 0.95rem;
}
.app-header .eyebrow {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    opacity: 0.7;
    margin: 0 0 0.1rem;
}

/* --- Tabs --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #fffaf2;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #d5c2a3;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    color: #705843;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    white-space: nowrap;
}
.stTabs [aria-selected="true"] {
    background: #0a6a72 !important;
    color: white !important;
    border-bottom: none !important;
}

/* --- Metrics --- */
[data-testid="stMetric"] {
    background: #fffaf2;
    border: 1px solid #d5c2a3;
    border-radius: 10px;
    padding: 1rem;
}
[data-testid="stMetric"] label {
    color: #705843;
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #0a6a72;
    font-weight: 700;
    font-family: 'Outfit', sans-serif;
}

/* --- Data Editor / Tables --- */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}

/* --- Buttons --- */
.stButton > button {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    border-radius: 8px;
    border: 1px solid #0a6a72;
    color: #0a6a72;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #0a6a72;
    color: white;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"] {
    background: #0a6a72;
    color: white;
    border-color: #0a6a72;
}

/* --- Popover (tooltips ?) --- */
[data-testid="stPopover"] button {
    background: #d9eff1 !important;
    color: #054f56 !important;
    border: 1px solid #0a6a72 !important;
    border-radius: 50% !important;
    width: 24px !important;
    height: 24px !important;
    min-width: 24px !important;
    padding: 0 !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: 0.35rem !important;
}

/* --- Number inputs --- */
[data-testid="stNumberInput"] input {
    font-family: 'Outfit', sans-serif;
    font-weight: 500;
}

/* --- Section dividers --- */
.section-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    color: #2b1f15;
    font-size: 1.1rem;
    border-bottom: 2px solid #0a6a72;
    padding-bottom: 0.3rem;
    margin: 1.5rem 0 1rem;
}

/* --- Cost cascade card --- */
.cascade-card {
    background: linear-gradient(135deg, #fffaf2 0%, #f4efe6 100%);
    border: 1px solid #d5c2a3;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.5rem 0;
}
.cascade-card .label {
    color: #705843;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.cascade-card .value {
    color: #0a6a72;
    font-size: 1.3rem;
    font-weight: 800;
    font-family: 'Outfit', sans-serif;
}

/* --- Sidebar --- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f4efe6 0%, #e8dfd0 100%);
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
    color: #2b1f15;
    font-family: 'Outfit', sans-serif;
}

/* --- Waterfall/Charts --- */
.js-plotly-plot .plotly .modebar {
    right: 10px !important;
}
</style>
"""


def inject_theme():
    """Inyecta el CSS del tema en la app Streamlit."""
    import streamlit as st
    st.markdown(ADEX_THEME_CSS, unsafe_allow_html=True)


def render_header():
    """Renderiza el header principal de la aplicacion."""
    import streamlit as st
    st.markdown(
        """
        <div class="app-header">
            <p class="eyebrow">ADEX &middot; Data Trade</p>
            <h1>Expediente de Costos de Importacion / Exportacion</h1>
            <p>Calculo tecnico de costos aterrizados, tributos aduaneros y precio de venta para operaciones de comercio exterior</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
