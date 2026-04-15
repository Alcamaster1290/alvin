"""Tab 1: Factura Comercial - Ingreso de SKUs y calculo FOB."""

import json
import streamlit as st
import pandas as pd
from decimal import Decimal
from engine.models import SkuLine, dec
from engine.invoice import compute_invoice, get_total_fob
from engine.contracts import load_trade_case, load_palletizer_legacy
from ui.components import section_title, format_usd, display_tooltip


def _load_from_palletizer_json(uploaded_file) -> list[dict]:
    """Parsea un JSON exportado del palletizer para extraer SKUs."""
    data = json.load(uploaded_file)
    skus = []

    multi_inputs = data.get("input", {}).get("multiSkuInputs", [])
    if multi_inputs:
        for item in multi_inputs:
            skus.append({
                "Producto": item.get("name", f"SKU-{item.get('skuId', '')}"),
                "Unidad": "UND",
                "Cantidad": item.get("quantity", 1),
                "Precio FOB Unitario (USD)": 0.0,
            })
    return skus


def render(state_key: str = "invoice"):
    """Renderiza el tab de factura comercial."""

    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "skus_df": pd.DataFrame({
                "Producto": ["Producto 1"],
                "Unidad": ["UND"],
                "Cantidad": [100],
                "Precio FOB Unitario (USD)": [10.00],
            })
        }

    section_title("Factura Comercial")

    col_info, col_tooltip = st.columns([10, 1])
    with col_info:
        st.markdown("Ingresa los productos de tu importacion/exportacion. El **FOB total** y la **proporcion** de cada SKU se calculan automaticamente.")
    with col_tooltip:
        display_tooltip("fob")

    # ── Import from Palletizer or add rows manually ──
    col_import, col_add = st.columns(2)

    with col_import:
        with st.expander("Importar productos desde ADEX Palletizer", expanded=False):
            st.markdown(
                "Si ya armaste tu caso de embalaje en **ADEX Palletizer**, "
                "puedes cargar el archivo JSON que exportaste y los productos "
                "se completaran automaticamente."
            )
            st.caption(
                "En Palletizer, usa el boton **\"Enviar a Costos\"** o "
                "**\"Exportar JSON\"** para descargar el archivo."
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
                        case_id, loaded_skus, meta = load_trade_case(raw)
                        rows = []
                        for s in loaded_skus:
                            rows.append({
                                "Producto": s.name,
                                "Unidad": s.unit,
                                "Cantidad": int(s.quantity),
                                "Precio FOB Unitario (USD)": float(s.fob_unit_price),
                            })
                        st.session_state[state_key]["skus_df"] = pd.DataFrame(rows)
                        st.session_state["trade_case_id"] = case_id
                        st.session_state["trade_case_meta"] = meta
                        st.success(
                            f"{len(rows)} producto(s) importados correctamente "
                            f"desde Palletizer."
                        )
                    else:
                        palletizer_skus = _load_from_palletizer_json(uploaded)
                        if palletizer_skus:
                            st.session_state[state_key]["skus_df"] = pd.DataFrame(
                                palletizer_skus
                            )
                            st.success(
                                f"{len(palletizer_skus)} producto(s) importados. "
                                f"Completa el **Precio FOB Unitario** de cada uno."
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
            "Cantidad de productos a agregar",
            min_value=1, max_value=500, value=1,
            key=f"{state_key}_num_rows",
        )
        if st.button("Agregar filas", key=f"{state_key}_add_rows"):
            current_df = st.session_state[state_key]["skus_df"]
            new_rows = pd.DataFrame({
                "Producto": [f"Producto {len(current_df) + i + 1}" for i in range(num_rows)],
                "Unidad": ["UND"] * num_rows,
                "Cantidad": [0] * num_rows,
                "Precio FOB Unitario (USD)": [0.0] * num_rows,
            })
            st.session_state[state_key]["skus_df"] = pd.concat(
                [current_df, new_rows], ignore_index=True
            )
            st.rerun()

    # Editable table
    edited_df = st.data_editor(
        st.session_state[state_key]["skus_df"],
        num_rows="dynamic",
        use_container_width=True,
        key=f"{state_key}_editor",
        column_config={
            "Producto": st.column_config.TextColumn("Producto", width="large"),
            "Unidad": st.column_config.SelectboxColumn(
                "Unidad", options=["UND", "KG", "LT", "MT", "PAR", "DOC", "CJ", "BLS", "TN"],
                width="small",
            ),
            "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, format="%d"),
            "Precio FOB Unitario (USD)": st.column_config.NumberColumn(
                "Precio FOB Unit. (USD)", min_value=0.0, format="%.4f",
            ),
        },
    )

    # Update state
    st.session_state[state_key]["skus_df"] = edited_df

    # Compute
    valid_df = edited_df.dropna(subset=["Producto"]).copy()
    valid_df = valid_df[valid_df["Cantidad"] > 0]

    if valid_df.empty:
        st.info("Agrega al menos un producto con cantidad mayor a 0.")
        return []

    skus = []
    for _, row in valid_df.iterrows():
        skus.append(SkuLine(
            name=str(row["Producto"]),
            unit=str(row.get("Unidad", "UND")),
            quantity=dec(row["Cantidad"]),
            fob_unit_price=dec(row["Precio FOB Unitario (USD)"]),
        ))

    skus = compute_invoice(skus)
    total_fob = get_total_fob(skus)

    # Results summary
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total FOB", format_usd(total_fob))
    with col2:
        st.metric("Numero de SKUs", str(len(skus)))
    with col3:
        st.metric("Unidades Totales", f"{sum(s.quantity for s in skus):,.0f}")

    # Proportions table
    with st.expander("Ver proporciones por SKU", expanded=False):
        prop_data = []
        for s in skus:
            prop_data.append({
                "Producto": s.name,
                "Cantidad": int(s.quantity),
                "FOB Unitario": float(s.fob_unit_price),
                "FOB Total": float(s.fob_total),
                "Proporcion (%)": float(s.proportion * 100),
            })
        st.dataframe(
            pd.DataFrame(prop_data),
            use_container_width=True,
            column_config={
                "FOB Unitario": st.column_config.NumberColumn(format="$%.4f"),
                "FOB Total": st.column_config.NumberColumn(format="$%.2f"),
                "Proporcion (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

    return skus
