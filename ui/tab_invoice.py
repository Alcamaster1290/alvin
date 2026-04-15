"""Tab 1: Factura Comercial - Ingreso de SKUs y calculo FOB.

Replica la hoja "Factura Comercial" del Excel CCi:
  - Columnas editables: Descripcion, Unidad, Cantidad, FOB Unitario
  - Columnas calculadas: FOB Total, Participacion
"""

import json
import streamlit as st
import pandas as pd
from decimal import Decimal
from engine.models import SkuLine, dec
from engine.invoice import compute_invoice, get_total_fob
from engine.contracts import load_trade_case, load_palletizer_legacy
from ui.components import section_title, format_usd, display_tooltip


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_UNIT_OPTIONS = [
    "Unid.", "Kg", "Lt", "Mt", "Par", "Doc", "Caja", "Bolsa", "Tn",
]

_EMPTY_ROW = {
    "Descripcion del Producto": "",
    "Unidad de Medida": "Unid.",
    "Cantidad": 0,
    "FOB Unitario (USD)": 0.0,
}

_DEFAULT_ROWS = 5  # filas vacias iniciales


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_df(n_rows: int = _DEFAULT_ROWS) -> pd.DataFrame:
    """Genera un DataFrame vacio con *n_rows* filas listas para editar."""
    return pd.DataFrame([dict(_EMPTY_ROW) for _ in range(n_rows)])


def _rows_from_trade_case(raw: dict) -> tuple[list[dict], str | None, dict]:
    """Extrae filas + metadata desde un trade-case.v1."""
    case_id, loaded_skus, meta = load_trade_case(raw)
    rows = []
    for s in loaded_skus:
        rows.append({
            "Descripcion del Producto": s.name,
            "Unidad de Medida": s.unit if s.unit in _UNIT_OPTIONS else "Unid.",
            "Cantidad": int(s.quantity),
            "FOB Unitario (USD)": float(s.fob_unit_price),
        })
    return rows, case_id, meta


def _rows_from_legacy_json(raw: dict) -> list[dict]:
    """Extrae filas desde un JSON legacy del palletizer."""
    multi_inputs = raw.get("input", {}).get("multiSkuInputs", [])
    rows = []
    for item in multi_inputs:
        rows.append({
            "Descripcion del Producto": item.get("name", f"SKU-{item.get('skuId', '')}"),
            "Unidad de Medida": "Unid.",
            "Cantidad": item.get("quantity", 1),
            "FOB Unitario (USD)": 0.0,
        })
    return rows


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(state_key: str = "invoice"):
    """Renderiza el tab de factura comercial."""

    # ── Estado inicial: filas vacias editables ──
    if state_key not in st.session_state:
        st.session_state[state_key] = {"skus_df": _make_empty_df()}

    section_title("Factura Comercial")

    col_info, col_tooltip = st.columns([10, 1])
    with col_info:
        st.markdown(
            "Ingresa los productos de tu operacion. "
            "El **FOB Total** y la **Participacion** de cada producto "
            "se calculan automaticamente."
        )
    with col_tooltip:
        display_tooltip("fob")

    # ── Importar / Agregar filas ──
    col_import, col_add = st.columns(2)

    with col_import:
        with st.expander("Importar productos desde ADEX Palletizer", expanded=False):
            st.markdown(
                "Si ya armaste tu caso de embalaje en **ADEX Palletizer**, "
                "puedes cargar el archivo JSON que exportaste y los productos "
                "se completaran automaticamente."
            )
            st.caption(
                'En Palletizer, usa el boton **"Enviar a Costos"** o '
                '**"Exportar JSON"** para descargar el archivo.'
            )
            uploaded = st.file_uploader(
                "Arrastra o selecciona el archivo JSON",
                type=["json"],
                key=f"{state_key}_json_upload",
            )
            if uploaded is not None:
                try:
                    raw = json.load(uploaded)
                    uploaded.seek(0)

                    if raw.get("version") == "trade-case.v1":
                        rows, case_id, meta = _rows_from_trade_case(raw)
                        st.session_state[state_key]["skus_df"] = pd.DataFrame(rows)
                        st.session_state["trade_case_id"] = case_id
                        st.session_state["trade_case_meta"] = meta
                        st.success(
                            f"{len(rows)} producto(s) importados correctamente "
                            f"desde Palletizer."
                        )
                    else:
                        rows = _rows_from_legacy_json(raw)
                        if rows:
                            st.session_state[state_key]["skus_df"] = pd.DataFrame(rows)
                            st.success(
                                f"{len(rows)} producto(s) importados. "
                                f"Completa el **FOB Unitario** de cada uno."
                            )
                        else:
                            st.warning(
                                "No se encontraron productos en el archivo. "
                                "Verifica que sea un JSON exportado de Palletizer."
                            )
                except ValueError as e:
                    st.error(f"El archivo no tiene el formato esperado: {e}")
                except Exception as e:
                    st.error(f"No se pudo leer el archivo: {e}")

    with col_add:
        num_rows = st.number_input(
            "Filas a agregar",
            min_value=1, max_value=500, value=5,
            key=f"{state_key}_num_rows",
        )
        if st.button("Agregar filas", key=f"{state_key}_add_rows", use_container_width=True):
            current_df = st.session_state[state_key]["skus_df"]
            new_rows = _make_empty_df(num_rows)
            st.session_state[state_key]["skus_df"] = pd.concat(
                [current_df, new_rows], ignore_index=True
            )
            st.rerun()

    # ── Tabla editable ──
    st.caption("Edita directamente cada celda. Usa el boton **+** de abajo para mas filas.")

    edited_df = st.data_editor(
        st.session_state[state_key]["skus_df"],
        num_rows="dynamic",
        use_container_width=True,
        key=f"{state_key}_editor",
        column_order=[
            "Descripcion del Producto",
            "Unidad de Medida",
            "Cantidad",
            "FOB Unitario (USD)",
        ],
        column_config={
            "Descripcion del Producto": st.column_config.TextColumn(
                "Descripcion del Producto",
                width="large",
                help="Nombre o descripcion del producto a importar/exportar",
            ),
            "Unidad de Medida": st.column_config.SelectboxColumn(
                "Unidad",
                options=_UNIT_OPTIONS,
                width="small",
                help="Unidad de medida comercial",
            ),
            "Cantidad": st.column_config.NumberColumn(
                "Cantidad",
                min_value=0,
                step=1,
                format="%d",
                help="Cantidad de unidades",
            ),
            "FOB Unitario (USD)": st.column_config.NumberColumn(
                "FOB Unit. (USD)",
                min_value=0.0,
                step=0.01,
                format="%.4f",
                help="Precio FOB por unidad en dolares americanos",
            ),
        },
    )

    # Guardar estado
    st.session_state[state_key]["skus_df"] = edited_df

    # ── Filtrar filas validas y calcular ──
    valid_mask = (
        edited_df["Descripcion del Producto"].astype(str).str.strip().ne("")
        & edited_df["Cantidad"].gt(0)
    )
    valid_df = edited_df.loc[valid_mask]

    if valid_df.empty:
        st.info("Completa al menos un producto con descripcion y cantidad mayor a 0.")
        return []

    skus: list[SkuLine] = []
    for _, row in valid_df.iterrows():
        skus.append(SkuLine(
            name=str(row["Descripcion del Producto"]).strip(),
            unit=str(row.get("Unidad de Medida", "Unid.")),
            quantity=dec(row["Cantidad"]),
            fob_unit_price=dec(row["FOB Unitario (USD)"]),
        ))

    skus = compute_invoice(skus)
    total_fob = get_total_fob(skus)

    # ── Resumen ──
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Monto Total FOB (USD)", format_usd(total_fob))
    with col2:
        st.metric("Productos", str(len(skus)))
    with col3:
        st.metric("Unidades Totales", f"{sum(s.quantity for s in skus):,.0f}")

    # ── Tabla de resultados (replica columnas I y J del Excel) ──
    results_data = []
    for i, s in enumerate(skus, start=1):
        results_data.append({
            "#": i,
            "Producto": s.name,
            "Cantidad": int(s.quantity),
            "FOB Unit. (USD)": float(s.fob_unit_price),
            "FOB Total (USD)": float(s.fob_total),
            "Participacion (%)": float(s.proportion * 100),
        })

    st.dataframe(
        pd.DataFrame(results_data),
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
            "Producto": st.column_config.TextColumn("Producto", width="large"),
            "Cantidad": st.column_config.NumberColumn("Cantidad", format="%d"),
            "FOB Unit. (USD)": st.column_config.NumberColumn(
                "FOB Unit. (USD)", format="$%.4f",
            ),
            "FOB Total (USD)": st.column_config.NumberColumn(
                "FOB Total (USD)", format="$%.2f",
            ),
            "Participacion (%)": st.column_config.NumberColumn(
                "Participacion", format="%.2f%%",
            ),
        },
    )

    return skus
