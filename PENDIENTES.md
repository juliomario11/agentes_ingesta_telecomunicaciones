# ✅ PENDIENTES — Cierre del Proyecto Final (Big Data UNAULA)

> Checklist vivo para coordinar el cierre del proyecto entre **varias sesiones de agentes**.
> Está alineado con la rúbrica oficial `PROYECTO FINAL.pdf` (docente: Yeis Livis Taborda, I‑2026).

## 🧭 Cómo usar este archivo (para agentes y humanos)

- Cada ítem es una casilla `- [ ]`. Al completarlo:
  1. Márcalo como `- [x]`.
  2. Cambia su **Estado** a `Finalizado` e indica **fecha** y **quién** lo hizo (agente/persona).
  3. Si dejó evidencia (captura, tabla, link de PR), enlázala junto al ítem.
- No borres ítems finalizados: sirven de bitácora.
- Si aparece trabajo nuevo, agrégalo en la sección correspondiente.

Convención de estado: `Pendiente` · `En progreso` · `Finalizado`.

---

## 📊 Estado global vs. rúbrica

| # | Componente (peso) | Estado |
|---|---|---|
| 1 | Caso de negocio (10%) | Finalizado |
| 2 | Relación beneficio/coste (10%) | En progreso (falta ROI cuantitativo) |
| 3 | Arquitectura propuesta (10%) | Finalizado |
| 4 | Pipeline de ingesta (50%) | En progreso (script listo; falta ejecutarlo y evidenciarlo) |
| 5 | Modelos de ciencia de datos (10%) | En progreso (modelo listo; falta análisis descriptivo) |
| 6 | App o visualización (10%) | En progreso (falta serving endpoint desplegado + capturas) |

---

## 🟢 Ya finalizado (bitácora)

- [x] Caso de negocio — `docs/caso_de_negocio.md`.
- [x] Arquitectura propuesta — `docs/arquitectura.md` + diagrama en README.
- [x] Análisis beneficio/costo (cualitativo) — `docs/beneficio_costo.md`.
- [x] Medallion poblado en Databricks: `bronze.tickets_noc` (1500), `silver.tickets_noc` (1500), `gold.decision_cuadrilla` (1500), vista `gold.notificaciones_whatsapp` (1311).
- [x] Modelo entrenado y **registrado en Unity Catalog**: `workspace.gold.modelo_decision_cuadrilla`.
- [x] CSV crudo subido al Volume `/Volumes/workspace/bronze/landing_zone/sample_tickets.csv`.
- [x] `sql/01_bronze.sql` modificado para **ingerir desde el Volume** (validado: 1500 filas, 0 nulos tras casteo).
- [x] Script de orquestación en Python: `pipeline/run_pipeline.py`.
- [x] Script de serving endpoint: `serving/deploy_serving_endpoint.py`.
- [x] README actualizado (enlace a GitHub, diagrama, modelo, pipeline, serving, autor).

---

## 🔴 Pendientes accionables

### 4. Pipeline de ingesta (50%) — automatización y evidencia
- [ ] Configurar entorno y ejecutar el pipeline de punta a punta. **Estado: Pendiente**
  ```bash
  export DATABRICKS_HOST="https://dbc-xxxx.cloud.databricks.com"
  export DATABRICKS_TOKEN="****"
  export DATABRICKS_WAREHOUSE_ID="xxxxxxxxxxxx"
  python pipeline/run_pipeline.py
  ```
  Evidencia esperada: salida con los conteos de `bronze → silver → gold`.
- [ ] Confirmar que `bronze.tickets_noc` quedó ingerido **desde el Volume** (no sintético) y pegar captura/linaje de Unity Catalog. **Estado: Pendiente**

### 6. App / Visualización (10%) — serving endpoint + dashboard
- [ ] Desplegar el serving endpoint y capturar evidencia. **Estado: Pendiente**
  ```bash
  python serving/deploy_serving_endpoint.py
  ```
  Evidencia esperada: endpoint `noc-decision-cuadrilla` activo + una invocación REST con su respuesta.
- [ ] Publicar un **Databricks SQL Dashboard** con `sql/04_dashboard_consultas.sql` y tomar **capturas en alta resolución**. **Estado: Pendiente**

### 5. Modelos de ciencia de datos (10%) — análisis descriptivo
- [ ] Crear y ejecutar un **análisis descriptivo / EDA** (resumen estadístico, distribuciones, correlaciones) sobre `silver`/`gold`; guardarlo en `notebooks/` o `docs/` con capturas. **Estado: Pendiente**

### 2. Relación beneficio/coste (10%) — cuantitativo
- [ ] Agregar a `docs/beneficio_costo.md` una sección de **ROI cuantitativo** e **ingreso‑vs‑costo** (con cifras ilustrativas y supuestos claros). **Estado: Pendiente**

### 📎 Recomendaciones del PDF (para el informe final)
- [ ] Anexo con **MLflow logs/métricas** del modelo (recall de `DESPACHAR_CUADRILLA`, accuracy, f1_macro). **Estado: Pendiente**
- [ ] Diagramas y capturas en **alta resolución**; fragmentos de código en **Courier New** en el documento final. **Estado: Pendiente**

### 🏁 Cierre
- [ ] Mergear el/los Pull Request a `main`. **Estado: Pendiente**
- [ ] Compilar el **informe final (PDF)** con las 6 secciones de la rúbrica y subirlo a `Entrega_BIGDATA`. **Estado: Pendiente**

---

*Generado por una sesión de agentes el 2026‑06‑19. Mantener actualizado en cada sesión.*
*Autor del proyecto: Mario Daniel Enrique Perez Jimenez.*
