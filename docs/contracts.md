# Contratos de Integracion - import_cost_calculator

Este modulo **consume** `trade-case.v1` y **produce** `trade-costs.v1`.

## trade-case.v1 (Consumidor)

Archivo JSON que describe un caso comercial generado por ADEX Palletizer u otra fuente.

**Campos utilizados por este modulo:**
- `caseId` — Referencia para vincular al trade-costs.v1 producido
- `skus[]` — Se mapean a `SkuLine`: `name`, `unit`, `quantity`, `fobUnitPrice`
- `skus[].hsCode` — Para referencia al seleccionar partida arancelaria (ad-valorem)
- `operationType` — Determina si se activan tabs de importacion, exportacion o ambos

**Campos informativos (no usados en calculo):**
- `packagingSummary`, `palletSummary`, `containerSummary` — Mostrados como contexto logistico
- `originCountry`, `destinationCountry`, `incoterm`, `modePreference` — Contexto del caso

**Compatibilidad legacy:** Se mantiene soporte transitorio para el formato JSON actual del Palletizer (`multiSkuInputs[]`). Se recomienda migrar a trade-case.v1.

**Schema:** Ver `contracts/trade-case.v1.schema.json` en la raiz del workspace.

## trade-costs.v1 (Productor)

Archivo JSON que contiene los resultados del calculo de costos.

**Campos producidos:**
- `caseId` — Copiado del trade-case.v1 de entrada
- `rates` — Tasas aplicadas (ImportRates)
- `customs` — Tributos aduaneros (CustomsTaxResult)
- `expenses` — Gastos de importacion (ImportExpenses)
- `allocationsBySku` — Prorrateo por SKU (SkuCostAllocation)
- `pricing` — Precios de venta (SkuSellingPrice)
- `exportCosts` — Costos de exportacion (ExportCostResult), null si no aplica
- `regulatoryBasis` — Supuestos regulatorios y vigencia de tasas

**Precision:** Todos los montos como strings para preservar `decimal.Decimal`.

**Schema:** Ver `contracts/trade-costs.v1.schema.json` en la raiz del workspace.

## Regla operativa

Toda integracion entre modulos pasa por `caseId` y contratos versionados.
