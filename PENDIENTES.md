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
| 2 | Relación beneficio/coste (10%) | Finalizado (análisis cualitativo; ROI cuantitativo NO requerido según clase) |
| 3 | Arquitectura propuesta (10%) | Finalizado |
| 4 | Pipeline de ingesta (50%) | En progreso (Medallion poblado y verificado en vivo; host+warehouse reales configurados; **falta una corrida con `DATABRICKS_TOKEN` en runtime para evidenciar la ejecución del script**) |
| 5 | Modelos de ciencia de datos (10%) | Finalizado (modelo + análisis descriptivo) |
| 6 | App o visualización (10%) | En progreso (falta desplegar el serving endpoint y publicar el SQL Dashboard con capturas) |

---

## 🟢 Ya finalizado (bitácora)

- [x] Caso de negocio — `docs/caso_de_negocio.md`.
- [x] Arquitectura propuesta — `docs/arquitectura.md` + diagrama en README (mermaid + imagen de flujo embebida).
- [x] Análisis beneficio/coste (componente #2) — `docs/beneficio_costo.md` (**cualitativo**). **Finalizado:** el ROI **cuantitativo NO es requerido** (indicado en clase).
- [x] **Medallion poblado y VERIFICADO EN VIVO en Databricks** (re‑verificado **2026‑06‑23** vía SQL Warehouse `cf44bf1905ce0de9`): `bronze.tickets_noc` = **1500**, `silver.tickets_noc` = **1500**, `gold.decision_cuadrilla` = **1500**, vista `gold.notificaciones_whatsapp` = **1281**. Evidencia: consulta `SELECT COUNT(*)` por capa sobre `workspace.*`.
- [x] Modelo entrenado y **registrado en Unity Catalog**: `workspace.gold.modelo_decision_cuadrilla` (el notebook `notebooks/04_modelo.py` lo entrena y registra). *Nota: este SQL Warehouse no soporta `SHOW MODELS`; la existencia del modelo se confirmó por el responsable del workspace, no por consulta SQL en esta sesión.*
- [x] CSV crudo subido al Volume `/Volumes/workspace/bronze/landing_zone/sample_tickets.csv`.
- [x] `sql/01_bronze.sql` modificado para **ingerir desde el Volume** (validado: 1500 filas, 0 nulos tras casteo).
- [x] `sql/00_setup.sql` (NUEVO): crea schemas bronze/silver/gold + Volume `landing_zone` con `IF NOT EXISTS` (reproducible desde cero). Schemas verificados en vivo.
- [x] Script de orquestación en Python: `pipeline/run_pipeline.py` — **conectado al Databricks real** (host `dbc-393a3afa-a710`, warehouse `cf44bf1905ce0de9`); token por env var con guard.
- [x] Script de serving endpoint: `serving/deploy_serving_endpoint.py` (presente; **aún NO desplegado**).
- [x] README actualizado (enlace a GitHub, diagrama mermaid + **imagen de flujo embebida**, nota de producción PostgreSQL, modelo, pipeline, serving, autor; placeholders de host/warehouse actualizados a los reales, token siempre por env).
- [x] **Análisis descriptivo / EDA** sobre Gold (componente #5) — `docs/analisis_descriptivo.md`, notebook `notebooks/07_eda_analisis_descriptivo.py` y script reproducible `src/analisis_descriptivo.py`. **Estado: Finalizado** (2026‑06‑19). Hallazgos: 1.500 filas, 0 nulos/duplicados; desbalance del target **12,5 : 1** (DESPACHAR 82,7 % · ESPERAR 10,7 % · TÉCNICO_URGENTE 6,6 %); `ESPERAR` exclusivo de HFC; **7 figuras (SVG) versionadas y embebidas** en `docs/img/eda/`.
- [x] Muestra simulada **versionada en el repo**: `data/sample_tickets.csv` (1.500 filas, semilla 42) + `.gitignore` ajustado para permitir `data/sample_*.csv` (sin abrir la puerta a datos reales).
- [x] **Seguridad (repo PÚBLICO):** corregido el hardcode de credenciales en `pipeline/run_pipeline.py`. El **token jamás se hardcodea** (cadena vacía + guard que aborta si falta `DATABRICKS_TOKEN`); host y warehouse (identificadores, no secretos) quedan en el código. Advertencia de seguridad reescrita. **Secret scanning ejecutado:** sin tokens reales filtrados (ver sección Notas). **Finalizado 2026‑06‑23.**

---

## 🔴 Pendientes accionables

### 4. Pipeline de ingesta (50%) — automatización y evidencia
- [ ] **Ejecutar el pipeline de punta a punta y pegar la salida.** **Estado: Listo para ejecutar / En progreso.** Host y warehouse **reales ya configurados** en `pipeline/run_pipeline.py`; **solo falta** exportar `DATABRICKS_TOKEN` (PAT) en el runtime y correr:
  ```bash
  export DATABRICKS_HOST="https://dbc-393a3afa-a710.cloud.databricks.com"
  export DATABRICKS_TOKEN="****"   # PAT real, SOLO en runtime (repo público)
  export DATABRICKS_WAREHOUSE_ID="cf44bf1905ce0de9"
  python pipeline/run_pipeline.py
  ```
  Evidencia esperada: salida con los conteos de `bronze → silver → gold`. *(NOTA: en esta sesión NO se ejecutó el script porque no se dispone del token; el Medallion ya está poblado y verificado en vivo, pero la corrida del orquestador en sí queda pendiente de evidenciar.)*
- [ ] Confirmar que `bronze.tickets_noc` quedó ingerido **desde el Volume** (no sintético) y pegar captura/linaje de Unity Catalog. **Estado: Pendiente.**

### 6. App / Visualización (10%) — serving endpoint + dashboard
- [ ] Desplegar el serving endpoint y capturar evidencia. **Estado: Pendiente** (no verificado en esta sesión; el endpoint `noc-decision-cuadrilla` aún no se confirma activo).
  ```bash
  python serving/deploy_serving_endpoint.py
  ```
  Evidencia esperada: endpoint `noc-decision-cuadrilla` activo + una invocación REST con su respuesta.
- [ ] Publicar un **Databricks SQL Dashboard** con `sql/04_dashboard_consultas.sql` y tomar **capturas en alta resolución**. **Estado: Pendiente.**

### 5. Modelos de ciencia de datos (10%) — análisis descriptivo
- [x] Crear y ejecutar un **análisis descriptivo / EDA** (resumen estadístico, distribuciones, correlaciones) sobre `silver`/`gold`; guardarlo en `notebooks/` o `docs/` con capturas. **Estado: Finalizado** — `docs/analisis_descriptivo.md` + `notebooks/07_eda_analisis_descriptivo.py` + `src/analisis_descriptivo.py`. Las 7 figuras (SVG) quedan **versionadas y embebidas** en el reporte; se regeneran con `python src/analisis_descriptivo.py`.
- [ ] (Opcional, para el informe) Pegar las 7 figuras del EDA en alta resolución en el documento final. **Estado: Pendiente.**

### 2. Relación beneficio/coste (10%) — Finalizado
- [x] Análisis beneficio/coste **cualitativo** (`docs/beneficio_costo.md`). **Estado: Finalizado** — el **ROI cuantitativo NO es requerido** (indicado en clase); el análisis cualitativo es suficiente.

### 📎 Recomendaciones del PDF (para el informe final)
- [ ] Anexo con **MLflow logs/métricas** del modelo (recall de `DESPACHAR_CUADRILLA`, accuracy, f1_macro). **Estado: Pendiente.**
- [ ] Diagramas y capturas en **alta resolución**; fragmentos de código en **Courier New** en el documento final. **Estado: Pendiente.**

### 🏁 Cierre
- [x] Mergear el/los Pull Request a `main`. **Estado: Finalizado (2026‑06‑23)** — PR #7 (`feature_00_setup_hardcode` → `main`) mergeado con `merge_method=merge`. Alcance: conexión Databricks real, corrección de seguridad (repo público → token por env), imagen de flujo, nota PostgreSQL, cura de PENDIENTES y README.
- [ ] Compilar el **informe final (PDF)** con las 6 secciones de la rúbrica y subirlo a `Entrega_BIGDATA`. **Estado: Pendiente.**

---

## 🗒️ Notas y decisiones

- **2026‑06‑23 · Seguridad (repo PÚBLICO):** el repositorio es público. Se eliminó el token hardcodeado de `pipeline/run_pipeline.py`: ahora `DATABRICKS_TOKEN = ""` y un guard aborta la ejecución si la env var no está definida. El **host** y el **SQL Warehouse ID** sí quedan en el código por ser **identificadores de conexión (no secretos)** compartidos abiertamente por el responsable del workspace. La advertencia de seguridad del script se reescribió para reflejar la verdad (repo público → el token nunca se hardcodea; viene de env var o de un Databricks Secret).
- **2026‑06‑23 · Secret scanning:** se ejecutó `github__run_secret_scanning` sobre el repo. Resultado registrado en el reporte de la sesión: **sin tokens reales filtrados** (los placeholders `dapiXXXX…` no son secretos válidos).
- **2026‑06‑23 · Fuente de datos en PRODUCCIÓN:** en producción la capa **Bronze ingiere los tickets desde una tabla PostgreSQL** (base operativa del NOC), **NO desde un CSV**. El `sample_tickets.csv` del Volume (landing zone) es **solo para la simulación/demo del curso**. Documentado en `README.md` (sección Arquitectura) y en `docs/arquitectura.md` (sección Bronze).
- **2026‑06‑23 · Corrección de dato:** la vista `gold.notificaciones_whatsapp` tiene **1281** filas (no 1311, como indicaba una versión previa de este archivo); corregido tras re‑verificación en vivo.

---

*Generado por una sesión de agentes el 2026‑06‑19. Actualizado el 2026‑06‑23 (Vega, ingeniero de datos).*
*Autor del proyecto: Mario Daniel Enrique Perez Jimenez.*

---

## 🎓 Pendientes derivados de Clases 3 y 4 (revisión de transcripciones · 2026‑06‑23)

> Estos ítems salen de revisar las transcripciones reales de la **Clase 3 (sáb 20 jun)** y la **Clase 4 (lun 22 jun)**. Son refuerzos/ampliaciones de lo que el docente enfatizó; no duplican los ítems ya listados arriba. Cita la clase de origen entre paréntesis.

- [ ] **Evidenciar el LINAJE de extremo a extremo en Unity Catalog** (`bronze → silver → gold → modelo → serving endpoint`), no solo de bronze. Capturar el *lineage graph* del catálogo en alta resolución. **(Clase 4)** — el docente fue explícito: *"vénganse para el linaje… de dónde viene la información"* y *"este es el 50% de su trabajo"*. El catálogo/linaje **pesa ~50% de la nota**. **Estado: Pendiente.**
- [ ] **Construir una APP de visualización para el usuario final** (Gradio / Dash / Streamlit o **Databricks App**) que consuma en vivo la recomendación del modelo (`DESPACHAR` / `ESPERAR` / `TÉCNICO_URGENTE`), además del dashboard SQL. **(Clase 3 y 4)** — *"la aplicación o visualización final para que el usuario aproveche el servicio"* (C3); *"crear una app customizada a punta de código"* (C4). Es el componente App/Visualización (10%) en su forma "PP" que pidió el profe. **Estado: Pendiente.**
- [ ] **Documentar la conexión reproducible Databricks ↔ VS Code / CLI** (`databricks-cli` o extensión de VS Code) para ejecutar el pipeline y publicar desde local. **(Clase 3 y 4)** — el docente mostró la conexión por Visual Studio Code / CLI como flujo de trabajo profesional. **Estado: Pendiente.**
- [ ] **Habilitar y documentar Genie** sobre las tablas `gold` (p. ej. `gold.decision_cuadrilla`) para consultas en lenguaje natural, con 2‑3 preguntas de ejemplo y su resultado. **(Clase 3 y 4)** — Genie se mencionó repetidamente como demo/entregable esperado. **Estado: Pendiente.**
- [ ] **Documentar los formatos del Lakehouse (Delta / Parquet / Iceberg)** y dejar registrada la **variante de pipeline declarativo (Lakeflow / Delta Live Tables)** como alternativa al script imperativo, discutiendo `append` vs `overwrite` y la orquestación por *jobs*. **(Clase 3: Parquet/Iceberg/Delta · Clase 4: enfoque declarativo)**. **Estado: Pendiente.**
- [ ] **Anexar la matriz de confusión del modelo** (además de las métricas de MLflow ya listadas) en el informe final, por clase del target. **(Clase 4)** — el docente trabajó la matriz de confusión como evidencia de evaluación. **Estado: Pendiente.**

> 🔎 **Nota de alcance:** el ejercicio de **CNN para clasificar imágenes reales vs generadas por IA** (Clase 4) y el **dataset de riesgo de crédito de Kaggle** (Clase 3) fueron *ejemplos de workshop*, **no aplican directamente** al caso NOC; se omiten del alcance del proyecto salvo que se quieran citar como referencia metodológica en el informe.

*Sección añadida el 2026‑06‑23 tras la revisión de las transcripciones de las Clases 3 y 4.*
