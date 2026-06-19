# Análisis Beneficio–Costo (Cualitativo)
## Proyecto: agentes_ingesta_telecomunicaciones
**UNAULA 2026 — Curso de Big Data**

---

## 1. Resumen Ejecutivo

El proyecto propone un pipeline de datos y un modelo de clasificación que apoya al NOC de un operador de telecomunicaciones colombiano en la decisión de despachar o no una cuadrilla ante una falla de red. Aproximadamente el 10 % de las incidencias son candidatas a autorrestablecerse (sin intervención humana), lo que representa un volumen no despreciable de desplazamientos potencialmente evitables. La solución, construida sobre Databricks Free Edition, genera una recomendación automática (DESPACHAR_CUADRILLA, ESPERAR_AUTORRESTABLECIMIENTO o TECNICO_URGENTE) que reduce el costo operativo, mejora la priorización y protege los niveles de servicio (SLA).

---

## 2. Contexto y Problema de Negocio

El NOC de un operador de telecomunicaciones opera redes HFC (con CMTS, nodos y monitoreo CACTI) y GPON (con OLT, ARPONES y monitoreo ZABBIX). Ante cada alarma, el analista de guardia debe decidir rápidamente si la falla requiere despachar una cuadrilla al sitio físico o si es prudente esperar.

Una señal crítica es el comportamiento de las fuentes de respaldo: cuando varios nodos de un mismo sector reportan simultáneamente operación en batería y la caída/recuperación ocurre en ventanas temporales muy similares, la causa raíz probable es un corte de energía eléctrica comercial externo. En ese escenario, el servicio se restablece solo al normalizarse la red eléctrica, sin necesidad de intervención técnica en campo.

El problema tiene dos caras con costos opuestos:

- **Falso despacho**: se envía una cuadrilla a una incidencia que se iba a autorresolver. Costo operativo real, sin beneficio para el cliente.
- **No despacho ante falla real**: el servicio permanece indisponible, se vulneran los SLA y se afecta la experiencia del cliente.

---

## 3. Costos de la Situación Actual (sin el proyecto)

### 3.1 Costo del falso despacho (incidencias candidatas a autorrestablecimiento)

| Categoría | Descripción cualitativa |
|---|---|
| Horas-hombre de cuadrilla | Tiempo del técnico desde la asignación hasta el cierre, incluyendo desplazamiento de ida y vuelta |
| Combustible y flota | Desgaste vehicular y consumo de combustible en desplazamientos innecesarios |
| Oportunidad | La cuadrilla despachada a una falla que se autorresuelve no está disponible para atender otra falla real simultánea |
| Costo de turno extendido | Si la autorización del despacho ocurre en horas nocturnas o festivas, el costo por hora-hombre es superior |

> **Supuesto ilustrativo:** si un operador mediano atiende del orden de cientos de incidencias mensuales y el 10 % son evitables, el volumen de desplazamientos innecesarios puede representar decenas de jornadas-técnico al mes. Sin inventar cifras exactas, el impacto acumulado es **alto** en operaciones de campo.

### 3.2 Costo del no-despacho ante una falla real

| Categoría | Descripción cualitativa |
|---|---|
| Indisponibilidad del servicio | Minutos u horas sin señal para los clientes del sector afectado |
| Penalizaciones por SLA | Créditos o compensaciones establecidos en contratos con clientes corporativos o en regulación de la CRC (Colombia) |
| Reputación y churn | Clientes residenciales y empresariales que perciben mala calidad de servicio pueden migrar al competidor |
| Escalamiento operativo | Una falla no atendida a tiempo puede agravarse y requerir intervención más costosa (TECNICO_URGENTE tardío) |

### 3.3 Costos intangibles generales

- Desgaste del equipo de guardia por decisiones bajo incertidumbre y presión.
- Falta de trazabilidad: sin linaje de datos, es difícil auditar por qué se tomó una decisión específica.
- Conocimiento tácito concentrado en pocos analistas expertos; el criterio no está sistematizado.

---

## 4. Beneficios del Proyecto

### 4.1 Reducción de despachos innecesarios

El modelo identifica las incidencias del segmento ESPERAR_AUTORRESTABLECIMIENTO (~10 % del total observado en el dataset de ejemplo). Cada despacho evitado correctamente se traduce en ahorro de horas-hombre, combustible y disponibilidad de la cuadrilla para fallas reales.

### 4.2 Priorización con clase TECNICO_URGENTE

El ~6 % de incidencias clasificadas como TECNICO_URGENTE corresponde a eventos graves (caída simultánea de nodos y arpones). Identificarlos temprano reduce el MTTR (tiempo medio de reparación) y limita la afectación masiva a clientes.

### 4.3 Mejor utilización de cuadrillas

Con una recomendación estructurada, el NOC puede asignar los recursos de campo de forma más racional: las cuadrillas disponibles se concentran en fallas reales, lo que mejora la productividad operativa global.

### 4.4 Cumplimiento de SLA

Una respuesta más oportuna y mejor priorizada reduce los tiempos de indisponibilidad, protegiendo los compromisos contractuales y regulatorios del operador.

### 4.5 Trazabilidad y gobierno de datos (Unity Catalog)

La arquitectura Medallion con Unity Catalog registra el linaje completo del dato: desde el evento crudo (Bronze) hasta la recomendación final (Gold). Esto permite auditar decisiones, identificar causas raíz de errores del modelo y demostrar cumplimiento ante entes reguladores.

### 4.6 Escalabilidad y reutilización

El pipeline puede incorporar nuevas fuentes (más CMTS, más OLT, datos meteorológicos, eventos de la red eléctrica) sin rediseñar la arquitectura. El modelo puede reentrenarse con datos reales una vez el sistema esté en producción.

---

## 5. Costos de Implementación y Operación de la Solución

| Componente | Naturaleza del costo |
|---|---|
| Desarrollo del pipeline y modelo | Horas del equipo de datos (ingeniería + ciencia de datos); costo principal del proyecto |
| Databricks Free Edition | **Sin costo de licencia**; elimina la barrera de entrada económica para el prototipo |
| Mantenimiento del pipeline | Monitoreo de jobs, corrección de derivas de datos, actualización de reglas Silver/Gold |
| Reentrenamiento del modelo | Periódico, a medida que se acumulan datos reales etiquetados por el NOC |
| Gobierno de datos | Definición de políticas de acceso, catálogo de activos y gestión de calidad del dato |
| Adopción y cambio cultural | Capacitación del personal de guardia; resistencia inicial al cambio de proceso |
| Riesgo de falsos negativos | Si el modelo recomienda ESPERAR y la falla era real, el costo es equivalente al escenario actual de no-despacho. Este riesgo debe gestionarse con umbrales de confianza y revisión humana. |

---

## 6. Comparación Beneficio–Costo (Tabla Cualitativa)

### 6.1 Tabla de valoración cualitativa

| Dimensión | Impacto del beneficio | Costo asociado | Balance |
|---|---|---|---|
| Reducción de despachos innecesarios | Alto | Bajo (modelo ya entrenado) | Favorable |
| Priorización TECNICO_URGENTE | Alto | Bajo | Muy favorable |
| Reducción de MTTR | Medio-Alto | Medio (mantenimiento) | Favorable |
| Cumplimiento de SLA | Alto | Bajo | Muy favorable |
| Trazabilidad/linaje | Medio | Bajo (Unity Catalog incluido) | Favorable |
| Cambio cultural / adopción | Bajo (riesgo) | Medio (capacitación) | Neutral-Favorable |
| Costo de desarrollo inicial | — | Medio-Alto | Inversión única |

### 6.2 Matriz de impacto

|  | **Probabilidad alta** | **Probabilidad media** |
|---|---|---|
| **Impacto alto** | Reducción de despachos innecesarios; Priorización urgente | Falso negativo del modelo (riesgo a gestionar) |
| **Impacto medio** | Mejora de SLA; Trazabilidad | Resistencia al cambio cultural |
| **Impacto bajo** | Escalabilidad futura | Deriva del modelo sin reentrenamiento |

---

## 7. Riesgos y Supuestos

| Riesgo / Supuesto | Descripción |
|---|---|
| **Supuesto:** datos simulados | El dataset de 1.500 tickets es sintético. El rendimiento real del modelo dependerá de la calidad y cantidad de datos históricos reales del operador. |
| **Supuesto ilustrativo:** distribución del 10 % | Se asume que aproximadamente 1 de cada 10 incidencias es candidata a autorrestablecimiento. Esta proporción puede variar según la geografía, la infraestructura y la red eléctrica local. |
| **Riesgo:** falsos negativos del modelo | El modelo puede clasificar erróneamente una falla real como candidata a espera. Mitigación: establecer umbral de confianza alto para ESPERAR y mantener revisión humana obligatoria. |
| **Riesgo:** adopción parcial | Si los analistas de guardia ignoran las recomendaciones del sistema, los beneficios no se materializan. |
| **Riesgo:** calidad del dato en origen | Si CACTI o ZABBIX no reportan con consistencia el estado de las baterías, la señal clave del modelo se degrada. |
| **Supuesto:** Databricks Free Edition | Se asume disponibilidad continua para el entorno académico/prototipo. En producción, una licencia comercial implicaría costos adicionales. |

---

## 8. Conclusión y Recomendación

El análisis cualitativo muestra que los **beneficios superan ampliamente los costos** en las dimensiones más críticas para el operador: reducción de desplazamientos innecesarios, mejor priorización de fallas graves y protección de los niveles de servicio. La principal inversión es el desarrollo inicial del pipeline y el modelo, mitigada por el uso de Databricks Free Edition sin costo de licencia.

Se recomienda avanzar hacia una prueba piloto con datos reales del NOC, comenzando por un periodo de operación en modo observación (el sistema recomienda, el analista decide) para validar la precisión del modelo y ganar confianza institucional antes de automatizar cualquier decisión. La trazabilidad garantizada por Unity Catalog facilita la auditoría continua y el ajuste progresivo del modelo.

El proyecto es técnicamente viable, estratégicamente relevante y económicamente justificable incluso en una evaluación cualitativa conservadora.
