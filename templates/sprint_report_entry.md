<!-- Template: sprint_report entry — una entrada por sesión, append-only -->

---

## Sesión: {{YYYY-MM-DD}} — {{TÍTULO_BREVE}}

**Código de handoff:** {{HO-AAAAMMDD-workstream-HHMM}}

<!-- At close, use the same code as the registry section. For a report-only supplement,
     use a unique new code and add **Handoff relacionado:** ORIGINAL_CODE after this field.
     Remove this instruction; never reuse an existing report code for different content. -->

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

### Estado completo para relevo

{{FULL_HANDOFF_SECTION_INSIDE_A_SAFE_MARKDOWN_FENCE}}

<!-- Replace every placeholder and remove instructional comments in the prepared UTF-8 input.
     Preserve the full section above, including next step, warnings, and root. Use a fence longer
     than every same-character fence in that section. Keep required fields; use N/A if inapplicable.
     Add a rescued-channel entry only when actual new or corrected context arrives through an
     authorized channel. Omit that entire block at normal close; do not leave an unfilled placeholder.
     Follow shared-protocol.md for source, timestamp, evidence labels, and append-report.
     Never reopen the original registry section or rewrite a prior report entry. -->
