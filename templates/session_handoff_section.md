<!-- Template: SESSION_HANDOFF.md — registro de handoffs vivos.
     Bloque 1 (HEADER) se escribe UNA sola vez, al crear el archivo.
     Bloque 2 (SECCIÓN) se INSERTA en cada cierre. Nunca sobrescribir el archivo completo. -->

<!-- ===== BLOQUE 1: HEADER DEL REGISTRO (solo al crear el archivo) ===== -->

# SESSION_HANDOFF — {{NOMBRE_PROYECTO}}

> Registro de handoffs. `[closed-pending] 🟢` vivo = sesión cerrada, aún no relevada ·
> `[closed] ✅` consumido = sesión cerrada y relevada, purgable.
> Reclamar: `/handoff resume <código>`   ·   Limpiar: `/handoff purge`

<!-- ===== BLOQUE 2: SECCIÓN DE HANDOFF (insertar una por cierre, estado [closed-pending] 🟢) =====
     La etiqueta [closed-pending] y el emoji 🟢 son un token pareado: transicionan juntos a
     [closed] ✅ al consumir. El emoji es la fuente canónica; la etiqueta es su alias grepeable. -->

## [closed-pending] 🟢 {{HO-AAAAMMDD-workstream-HHMM}} — {{workstream}}

> Proyecto: {{NOMBRE_PROYECTO}} · raíz: {{/ruta/absoluta/del/proyecto}}
> Canal: {{nombre-sesión}} [{{ref}}] · capturado {{AAAA-MM-DD HH:MM}}  (pista — reverificar antes de enviar)
> Generado: {{YYYY-MM-DD HH:MM}} [estimado]

<!-- La línea "Canal" identifica la sesión que escribió este handoff, tal como la imprime ListAgents.
     Es OBLIGATORIA: si el canal no está disponible se escribe "> Canal: no disponible", no se omite.
     Es una PISTA para buscar, no una dirección para enviar — el [ref] es un handle de runtime que
     puede caducar. Quien releve reverifica contra un ListAgents fresco. -->

<!-- La línea "Proyecto · raíz" es el vínculo de proyecto: la sesión receptora la compara
     contra su pwd (RECEPCIÓN Paso 0). Si no coincide, para en seco y no consume el handoff. -->


### Estado actual del workstream

{{2-4 líneas: qué es el proyecto, en qué punto está este workstream, qué se completó}}

### Última sesión — Resumen

- **Fecha:** {{YYYY-MM-DD}}
- **Objetivo:** {{1-2 líneas}}
- **Plan ejecutado:** {{título del plan o "Sin plan formal previo"}}
- **Resultado:** {{completado / parcial / con desviaciones — breve}}

### Siguiente paso concreto

- **Fase:** {{nombre/número de la siguiente fase}}
- **Descripción:** {{qué hay que hacer}}
- **Archivos involucrados:** {{rutas clave}}
- **Precondiciones:** {{qué debe estar listo antes de empezar}}

### Advertencias activas

- **Deuda técnica pendiente:** {{shortcut/workaround — contexto}} (o "N/A")
- **Blockers externos:** {{descripción — de quién depende, desde cuándo}} (o "N/A")
- **Decisiones que NO revertir sin contexto:** {{decisión — por qué, riesgo de revertir}} (o "N/A")

### Estado del repo

- **Rama:** {{nombre_rama}}
- **Último commit:** {{hash_7_chars}}
- **Último zip entregado:** {{versión o "N/A"}}

### Archivos clave para retomar

1. `SESSION_HANDOFF.md` — esta sección, por su código
2. `sprint_report.md` — entrada con el mismo código `{{HO-...}}`
3. `AUDIT_LOG.md` — si existe (bugs pendientes y clasificación)

<!-- Al consumir (modo resume), esta sección entera se reemplaza por su tombstone
     (etiqueta y emoji transicionan juntos: [closed-pending] 🟢 → [closed] ✅):
     ## [closed] ✅ {{HO-...}} — {{workstream}} · consumido {{AAAA-MM-DD}} · detalle en sprint_report.md -->
