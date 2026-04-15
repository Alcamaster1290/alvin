# ALVIN — Asistente Logistico Virtual Inteligente

Plataforma de comercio exterior para peruanos emprendedores que deseen exportar e importar con facilidad.

## Expediente de Costos de Importacion y Exportacion

Herramienta de calculo tecnico de costos aterrizados para operaciones de comercio exterior en Peru. Parte del ecosistema **ADEX Data Trade**.

### Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Flujo del expediente

1. **Factura Comercial** — FOB por SKU (manual o importado desde ADEX Palletizer)
2. **Configuracion** — Tasas arancelarias, seguro, agente, tipo de cambio
3. **Tributos Aduaneros** — CIF, Ad-Valorem, ISC, IGV, IPM, Percepcion
4. **Gastos de Importacion** — 21 conceptos editables
5. **Costo por Producto** — Prorrateo proporcional al FOB
6. **Precio de Venta** — Margen configurable por SKU
7. **Costos de Exportacion** — Logistica, documentacion, agente
8. **Dashboard** — KPIs, graficos, exportar Excel o JSON

### Integracion con el ecosistema

```
ADEX Palletizer  --trade-case.v1-->  ALVIN  --trade-costs.v1-->  SisLoPe
```

| Contrato | Direccion | Descripcion |
|----------|-----------|-------------|
| `trade-case.v1` | Entrada | SKUs, embalaje, paletizacion (desde ADEX Palletizer) |
| `trade-costs.v1` | Salida | Tributos, gastos, prorrateo, precios |

Schemas de referencia: [adex-palletizer/contracts/](https://github.com/Alcamaster1290/adex-palletizer/tree/main/contracts)

### Precision financiera

Aritmetica `decimal.Decimal` con redondeo `ROUND_HALF_UP`, replicando exactamente las funciones `ROUND()` de Excel.

### Tests

```bash
python -m pytest tests/ -v
```

109 tests cubren invoice, customs, allocation, pricing y export.

### Normativa de referencia

- Ley General de Aduanas (D.L. 1053)
- Reglamento LGA (D.S. 010-2009-EF)
- Arancel de Aduanas (D.S. 342-2016-EF)
- TUO Ley IGV e ISC (D.S. 055-99-EF)
- Regimen de Percepciones (Ley 29173)

---

ADEX Data Trade v1.0 | by Alvaro Caceres
