<!-- Template: SESSION_HANDOFF.md — registro de handoffs vivos.
     Bloque 1 (HEADER) se escribe UNA sola vez, al crear el archivo.
     Bloque 2 (SECCIÓN) se INSERTA en cada cierre. Nunca sobrescribir el archivo completo. -->

<!-- ===== BLOQUE 1: HEADER DEL REGISTRO (solo al crear el archivo) ===== -->

# SESSION_HANDOFF — {{NOMBRE_PROYECTO}}

> Registro de handoffs. 🟢 vivo = aún no retomado · ✅ consumido = purgable.
> Reclamar: `/handoff resume <código>`   ·   Limpiar: `/handoff purge`

<!-- ===== BLOQUE 2: SECCIÓN DE HANDOFF (insertar una por cierre, estado 🟢) ===== -->

## 🟢 {{HO-AAAAMMDD-workstream-HHMM}} — {{workstream}}

> Generado: {{YYYY-MM-DD HH:MM}} [estimado]

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

<!-- Al consumir (modo resume), esta sección entera se reemplaza por su tombstone:
     ## ✅ {{HO-...}} — {{workstream}} · consumido {{AAAA-MM-DD}} · detalle en sprint_report.md -->
