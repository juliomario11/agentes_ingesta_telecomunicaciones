# Caso de negocio — Despacho inteligente de cuadrillas en el NOC

## Contexto

Un **NOC (Network Operations Center)** opera una red de acceso con dos tecnologías:

- **HFC** (cable coaxial/híbrido): jerarquía `CMTS → INTERFAZ → NODO`.
- **GPON** (fibra): jerarquía `OLT → INTERFAZ → ARPON`.

Un mismo **ticket** puede agrupar varios de estos elementos. En HFC, los nodos pueden colgar de un **cable padre** común, de un **cable hijo**, o ser independientes; además cuentan con **fuentes de respaldo** (baterías de corta duración) que reportan por un **endpoint** su **voltaje** y **amperaje**.

## Problema

No todas las fallas requieren intervención física. Una porción relevante de los tickets se **restablece de forma autónoma**, típicamente cuando la causa raíz es **externa a la red** (corte de **energía eléctrica comercial** en el sector). La señal de la fuente de respaldo lo delata: si el nodo está **consumiendo batería** (no pegado a la red comercial) y varios nodos del mismo sector están igual, lo más probable es una falla eléctrica que se resolverá sola.

Despachar cuadrilla en esos casos genera **costo operativo, desgaste y desplazamientos en vano**. No despachar ante una falla real prolonga la **indisponibilidad** y afecta SLA.

## Pregunta de negocio

> Dado un ticket nuevo (uno o varios elementos NODO/ARPON), ¿conviene **despachar la cuadrilla** o **esperar al autorrestablecimiento**?

## Solución propuesta

Usar el **histórico de tickets** para:

1. **Clasificar** la incidencia (tecnología, elementos, sector, impacto/urgencia).
2. **Recuperar soluciones anteriores** sobre el mismo elemento o patrón.
3. **Recomendar la acción** (`DESPACHAR_CUADRILLA` / `ESPERAR_AUTORRESTABLECIMIENTO`) con score y justificación.
4. **Disparar notificaciones** a grupos de WhatsApp según reglas de negocio.

## Reglas de notificación a WhatsApp

Se notifica al grupo correspondiente cuando:

- El elemento es **VIP** (`NODO_VIP = true`).
- **Clientes afectados > 2000**.
- **Impacto** alto (p. ej. `Alto` / `Critico`).
- **Urgencia** alta (p. ej. `Alta` / `Critica`).

## Variable objetivo (target)

`accion_recomendada` ∈ { `DESPACHAR_CUADRILLA`, `ESPERAR_AUTORRESTABLECIMIENTO` }, derivada del desenlace histórico:

- Tickets cerrados **sin intervención física** y con señal de batería/energía externa → `ESPERAR_AUTORRESTABLECIMIENTO`.
- Tickets que **requirieron cuadrilla** para restablecer → `DESPACHAR_CUADRILLA`.

> ⚠️ Importa más evitar **falsos “esperar”** (no despachar una falla real) que falsos “despachar”. El modelo se evaluará priorizando **recall** sobre la clase `DESPACHAR_CUADRILLA`.

## Beneficio esperado (a cuantificar en el análisis beneficio–costo)

- Reducción de **despachos innecesarios** → ahorro operativo.
- Mejor **priorización** de cuadrillas hacia fallas reales.
- Base para un **agente de recomendación** integrado al flujo del NOC.

## Pendientes

- [ ] Generar **dataset simulado** (no existe data pública de este dominio).
- [ ] Validar el diccionario de datos y definir el target con reglas claras.
- [ ] Completar el análisis beneficio–costo (cualitativo).
