<!-- Template: sprint_report entry — una entrada por sesión, append-only -->

---

## Sesión: {{YYYY-MM-DD}} — {{TÍTULO_BREVE}}

**Código de handoff:** {{HO-AAAAMMDD-workstream-HHMM}}  <!-- mismo código que la sección en SESSION_HANDOFF.md -->

**Timestamps:**
- Inicio aproximado: {{HH:MM}} [estimado]
- Cierre aproximado: {{HH:MM}} [estimado]
- Duración estimada: {{Xh Ym}} [estimado]

### Objetivo de la sesión

{{1-2 líneas describiendo qué se buscaba lograr}}

### Plan referenciado

{{Título exacto del plan y/o archivo donde vive. Si no hubo plan formal: "Sin plan formal previo"}}

### Fases completadas

| # | Fase | Resultado | Plan origen |
|---|------|-----------|-------------|
| {{n}} | {{descripción}} | {{completada / completada con desviaciones / parcial / abortada}} | {{referencia al plan o "Sin plan formal"}} |

### Archivos tocados

**Creados:**
- {{ruta/completa/archivo}} — {{descripción de una línea}}

**Modificados:**
- {{ruta/completa/archivo}} — {{descripción del cambio}}

**Eliminados:**
- {{ruta/completa/archivo}} — {{razón}}

### Decisiones técnicas

- **{{Decisión}}:** {{Justificación — por qué, no solo qué}}

### Bugs detectados

{{Si AUDIT_LOG.md existe y fue actualizado en esta sesión:}}
- [{{severidad}}] {{descripción}} — ver AUDIT_LOG.md entrada {{fecha}}

{{Si no hay AUDIT_LOG.md o no se detectaron bugs: "N/A"}}

### Deuda técnica generada

- {{Shortcut/workaround/TODO}} — {{contexto de por qué se dejó pendiente}}

### Blockers externos activos

- {{Descripción del blocker}} — {{de quién/qué depende}}

### Estado del repo al cierre

- **Rama:** {{nombre_rama}}
- **Último commit:** {{hash_7_chars}}
- **Último zip entregado:** {{versión o "N/A"}}
