"""Tab 1: Factura Comercial - Ingreso de SKUs y calculo FOB.

Replica la hoja "Factura Comercial" del Excel CCi:
  - Formulario para agregar productos uno a uno
  - Importacion masiva desde ADEX Palletizer (JSON)
  - Tabla de resultados con FOB Total y Participacion calculados
"""

import json
import streamlit as st
import pandas as pd
from decimal import Decimal
from engine.models import SkuLine, dec
from engine.invoice import compute_invoice, get_total_fob
from engine.contracts import load_trade_case
from ui.components import section_title, format_usd, display_tooltip


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_UNIT_OPTIONS = [
    "Unid.", "Kg", "Lt", "Mt", "Par", "Doc", "Caja", "Bolsa", "Tn",
]

_SK = "invoice_products"  # session_state key for the product list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_state():
    """Inicializa la lista de productos si no existe."""
    if _SK not in st.session_state:
        st.session_state[_SK] = []


def _add_product(name: str, unit: str, qty: int, price: float):
    """Agrega un producto a la lista."""
    _ensure_state()
    st.session_state[_SK].append({
        "name": name.strip(),
        "unit": unit,
        "qty": qty,
        "price": price,
    })


def _remove_product(idx: int):
    """Elimina un producto por indice."""
    _ensure_state()
    if 0 <= idx < len(st.session_state[_SK]):
        st.session_state[_SK].pop(idx)


def _clear_products():
    """Limpia todos los productos."""
    st.session_state[_SK] = []


def _set_products_from_trade_case(raw: dict):
    """Carga productos desde un trade-case.v1."""
    case_id, loaded_skus, meta = load_trade_case(raw)
    products = []
    for s in loaded_skus:
        products.append({
            "name": s.name,
            "unit": s.unit if s.unit in _UNIT_OPTIONS else "Unid.",
            "qty": int(s.quantity),
            "price": float(s.fob_unit_price),
        })
    st.session_state[_SK] = products
    st.session_state["trade_case_id"] = case_id
    st.session_state["trade_case_meta"] = meta
    return len(products), case_id


def _set_products_from_legacy(raw: dict) -> int:
    """Carga productos desde un JSON legacy del palletizer."""
    multi_inputs = raw.get("input", {}).get("multiSkuInputs", [])
    products = []
    for item in multi_inputs:
        products.append({
            "name": item.get("name", f"SKU-{item.get('skuId', '')}"),
            "unit": "Unid.",
            "qty": item.get("quantity", 1),
            "price": 0.0,
        })
    if products:
        st.session_state[_SK] = products
    return len(products)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(state_key: str = "invoice"):
    """Renderiza el tab de factura comercial."""

    _ensure_state()
    products = st.session_state[_SK]

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

    # ── Importar desde Palletizer ──
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
                    count, case_id = _set_products_from_trade_case(raw)
                    st.success(f"{count} producto(s) importados desde Palletizer.")
                else:
                    count = _set_products_from_legacy(raw)
                    if count:
                        st.success(
                            f"{count} producto(s) importados. "
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

    # ── Formulario para agregar producto ──
    section_title("Agregar Producto")

    with st.form("add_product_form", clear_on_submit=True):
        fc1, fc2, fc3, fc4 = st.columns([4, 1.5, 1.5, 2])
        with fc1:
            f_name = st.text_input(
                "Descripcion del Producto",
                placeholder="Ej: Cable USB-C Trenzado 1m",
            )
        with fc2:
            f_unit = st.selectbox("Unidad", options=_UNIT_OPTIONS)
        with fc3:
            f_qty = st.number_input("Cantidad", min_value=0, step=1, value=0)
        with fc4:
            f_price = st.number_input(
                "FOB Unitario (USD)",
                min_value=0.0, step=0.01, format="%.4f", value=0.0,
            )

        submitted = st.form_submit_button(
            "Agregar producto", use_container_width=True
        )
        if submitted:
            if not f_name.strip():
                st.warning("Ingresa la descripcion del producto.")
            elif f_qty <= 0:
                st.warning("La cantidad debe ser mayor a 0.")
            else:
                _add_product(f_name, f_unit, f_qty, f_price)
                st.rerun()

    # ── Lista de productos agregados ──
    products = st.session_state[_SK]

    if not products:
        st.info(
            "Aun no has agregado productos. Usa el formulario de arriba "
            "o importa desde ADEX Palletizer."
        )
        return []

    section_title(f"Productos ({len(products)})")

    # Mostrar cada producto con opcion de editar y eliminar
    to_delete = None

    for i, prod in enumerate(products):
        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 4, 1.2, 1.5, 2, 0.8])
            with c1:
                st.markdown(f"**{i+1}**")
            with c2:
                new_name = st.text_input(
                    "Producto", value=prod["name"],
                    key=f"pn_{i}", label_visibility="collapsed",
                )
            with c3:
                idx_unit = (
                    _UNIT_OPTIONS.index(prod["unit"])
                    if prod["unit"] in _UNIT_OPTIONS else 0
                )
                new_unit = st.selectbox(
                    "Unidad", options=_UNIT_OPTIONS, index=idx_unit,
                    key=f"pu_{i}", label_visibility="collapsed",
                )
            with c4:
                new_qty = st.number_input(
                    "Cantidad", value=prod["qty"], min_value=0, step=1,
                    key=f"pq_{i}", label_visibility="collapsed",
                )
            with c5:
                new_price = st.number_input(
                    "FOB Unit.", value=prod["price"],
                    min_value=0.0, step=0.01, format="%.4f",
                    key=f"pp_{i}", label_visibility="collapsed",
                )
            with c6:
                if st.button("Eliminar", key=f"pd_{i}", type="secondary"):
                    to_delete = i

            # Actualizar valores en session_state si cambiaron
            prod["name"] = new_name
            prod["unit"] = new_unit
            prod["qty"] = new_qty
            prod["price"] = new_price

    # Procesar eliminacion fuera del loop
    if to_delete is not None:
        _remove_product(to_delete)
        st.rerun()

    # Boton limpiar todo
    st.markdown("")
    if st.button("Limpiar todos los productos", type="secondary"):
        _clear_products()
        st.rerun()

    # ── Filtrar validos y calcular ──
    skus: list[SkuLine] = []
    for prod in products:
        name = str(prod["name"]).strip()
        qty = prod["qty"]
        if name and qty > 0:
            skus.append(SkuLine(
                name=name,
                unit=str(prod["unit"]),
                quantity=dec(qty),
                fob_unit_price=dec(prod["price"]),
            ))

    if not skus:
        st.info("Completa al menos un producto con descripcion y cantidad mayor a 0.")
        return []

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
