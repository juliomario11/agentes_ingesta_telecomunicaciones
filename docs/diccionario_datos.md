# Diccionario de datos — tickets del NOC (simulados)

> No existe data pública de este dominio, por lo que el dataset es **simulado** con patrones realistas. Una falla eléctrica externa pone a varios nodos del mismo sector **en batería** y suele terminar en **autorrestablecimiento**.

## Columnas del ticket (Bronze)

| Columna | Tipo | Descripción |
|---|---|---|
| `ticket` | string | Identificador único del ticket |
| `departamento` | string | Departamento (Colombia) |
| `ciudad` | string | Ciudad |
| `territorialidad` | string | Zona/territorio operativo |
| `itsm_servicenow` | string | ID del caso en ServiceNow (ITSM) |
| `workorder_salesforce` | string | ID de la orden de trabajo en Salesforce |
| `clientes_afectados` | int | Número de clientes afectados |
| `tecnologia` | string | `HFC` o `GPON` |
| `cantidad_nodos` | int | Nodos involucrados (HFC) |
| `cantidad_arpones` | int | Arpones involucrados (GPON) |
| `cmts` / `olt` | string | Cabecera según tecnología |
| `interfaz` | string | Interfaz afectada |
| `cable_padre` | string | Cable padre del que cuelga el nodo (HFC) |
| `cable_hijo` | string | Cable hijo (HFC), si aplica |
| `nodo_vip` | bool | Elemento prioritario (VIP) |
| `impacto` | string | `Bajo` / `Medio` / `Alto` / `Critico` |
| `urgencia` | string | `Baja` / `Media` / `Alta` / `Critica` |
| `grupo_whatsapp` | string | Grupo de WhatsApp asociado |
| `descripcion` | string | Descripción de la falla |
| `resumen` | string | Resumen corto |
| `tecnico_asignado` | string | Técnico (anonimizado) |
| `avances` | string | Bitácora de avances |
| `adjuntos` | int | N.º de adjuntos |
| `existe_en_cacti` | bool | Si el elemento está monitoreado en Cacti |
| `fecha_apertura` | timestamp | Apertura del ticket |
| `fecha_cierre` | timestamp | Cierre del ticket |

## Region

`region` ∈ { `COSTA`, `ANDINA`, `ORIENTE`, `BOGOTA`, `SUR` } — macro-región operativa en Colombia (de mayor nivel que `departamento` / `ciudad`).

## Histórico de reparación y monitoreo

| Columna | Tipo | Descripción |
|---|---|---|
| `forma_resolucion` | string | Cómo se resolvió: `AUTORRESTABLECIMIENTO`, `CUADRILLA`, `TECNICO_URGENTE` |
| `restablecio_autonomo` | bool | El servicio volvió solo, sin intervención física |
| `hora_caida` | timestamp | Momento en que cayó el servicio |
| `hora_restablecimiento` | timestamp | Momento en que volvió el servicio |
| `fuente_monitoreo` | string | `CACTI` (HFC) o `ZABBIX` (GPON) |
| `correlacion_grafica_monitoreo` | bool | Si la caída/recuperación se vio casi a la misma hora en Cacti (HFC) o Zabbix (GPON) — fuerte indicio de causa eléctrica externa → autorrestablecimiento |
| `delta_correlacion_min` | int | Minutos de diferencia entre el evento del ticket y el evento visto en la gráfica de monitoreo |
| `falla_simultanea_nodo_arpon` | bool | Daño grave que tumba **NODOS y ARPONES al tiempo** → requiere **técnico urgente** |
| `solucion_aplicada` | string | Nota de cierre / solución histórica aplicada al elemento |

## Telemetría de energía (HFC — fuente de respaldo)

| Columna | Tipo | Descripción |
|---|---|---|
| `fuente_voltaje` | float | Voltaje reportado por el endpoint de la fuente |
| `fuente_amperaje` | float | Amperaje reportado |
| `flag_en_bateria` | bool | Derivado: el nodo consume batería (sin red comercial) |
| `nodos_sector_en_bateria` | int | Nodos del mismo sector/cable padre en batería |

## Features derivadas (Silver/Gold)

| Columna | Tipo | Descripción |
|---|---|---|
| `tiempo_resolucion_min` | int | Minutos entre apertura y cierre |
| `pct_autorrestablecimiento_nodo` | float | Histórico del nodo que se auto-resolvió |
| `requiere_notificacion` | bool | Aplica regla VIP / >2000 / impacto / urgencia |

## Target

| Columna | Valores | Descripción |
|---|---|---|
| `accion_recomendada` | `DESPACHAR_CUADRILLA`, `ESPERAR_AUTORRESTABLECIMIENTO`, `TECNICO_URGENTE` | Decisión a predecir |

### Lógica del target (para la data simulada)

- `falla_simultanea_nodo_arpon = true` (tumba NODOS y ARPONES a la vez) → **`TECNICO_URGENTE`**.
- `flag_en_bateria = true` + varios nodos del sector en batería + `correlacion_grafica_monitoreo = true` (visto casi a la misma hora en Cacti/Zabbix) → **`ESPERAR_AUTORRESTABLECIMIENTO`**.
- En el resto de casos (falla real sin indicios de causa eléctrica externa) → **`DESPACHAR_CUADRILLA`**.

> Para entrenar también se conserva la columna `forma_resolucion` (desenlace real histórico), de la que se deriva el target.
