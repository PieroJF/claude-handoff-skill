---
name: handoff
description: Cierra y releva sesiones de trabajo en proyectos con múltiples workstreams en paralelo. Tres modos. (1) CIERRE — `/handoff` o frases inequívocas de cierre ("cierra la sesión", "guarda el progreso", "termina la sesión", "haz el handoff", "vamos a cerrar", "session closure", "wrap up"): genera entrada en sprint_report.md (acumulativo) e inserta una sección codificada en SESSION_HANDOFF.md (registro de handoffs vivos) SIN sobrescribir las de otras sesiones, más un bloque de relevo en chat. (2) RECEPCIÓN — `/handoff resume [código]` o "retoma la sesión", "continúa el workstream X", "relevo de handoff": vuelca un handoff vivo y lo marca consumido. (3) PURGA — `/handoff purge [código]`, "limpia handoffs consumidos": borra solo secciones ya consumidas. NO usar para auditorías de código (otra skill). NO disparar ante frases ambiguas como "guarda esto" o "termina esto" referidas a tareas puntuales. Asume que la implementación de la sesión ya está completa y que la auditoría técnica relevante ya se ejecutó por separado.
---

# Skill: Handoff — Cierre y Relevo de Sesión Multi-Workstream

## Propósito

Esta skill gestiona el cierre y relevo de sesiones de trabajo en proyectos donde el
usuario corre **varias sesiones en paralelo sobre distintos workstreams** (ej: `landing`,
`proveedor-pms`, `onboarding`). Produce y mantiene tres artefactos:

1. **`sprint_report.md`** — Append-only. Historial acumulativo de TODAS las sesiones del
   proyecto. Responde "¿qué hicimos en esta sesión?". Es el `git log`.
2. **`SESSION_HANDOFF.md`** — **Registro de handoffs vivos**, NO un snapshot sobrescribible.
   Cada handoff es una sección con código único y estado (🟢 vivo / ✅ consumido). Varios
   handoffs de distintos workstreams coexisten. Responde "¿qué relevos hay pendientes y
   cómo se retoma cada uno?".
3. **Bloque de relevo en chat** — Copy-paste inmediato para arrancar una sesión nueva.
   Lleva el código del handoff para que la sesión receptora lo reclame sin abrir archivos.

## Por qué cambió el modelo (NO lo ignores)

`SESSION_HANDOFF.md` **dejó de ser un snapshot que se sobrescribe**. Antes, cada cierre
sobrescribía el archivo completo. Con varias sesiones en paralelo eso **destruía** el
handoff que una sesión hermana aún no había retomado (caso real documentado: 4 overwrites
en un día, estado intermedio perdido). El modelo nuevo es **aditivo y codificado**: cada
cierre inserta su propia sección con código único; nada vivo se sobrescribe jamás.

## Modelo de datos — `SESSION_HANDOFF.md`

```markdown
# SESSION_HANDOFF — <proyecto>
> Registro de handoffs. 🟢 vivo = aún no retomado · ✅ consumido = purgable.
> Reclamar: /handoff resume <código>   ·   Limpiar: /handoff purge

## 🟢 HO-20260529-landing-1834 — landing
（detalle completo del handoff: ver template de sección）

## 🟢 HO-20260529-proveedor-pms-1620 — proveedor-pms
（detalle completo…）

## ✅ HO-20260528-onboarding-2210 — onboarding · consumido 2026-05-29 · detalle en sprint_report.md
```

**Ciclo de vida (unidireccional):**

```
🟢 vivo  ──/handoff resume <código>──▶  ✅ consumido (tombstone)  ──/handoff purge──▶  (borrado)
```

**REGLA CENTRAL (no negociable):** borrar o reescribir una sección SOLO es legal si está
✅. Una sección 🟢 es **intocable**, salvo por el `resume` que la transiciona a ✅.

**Código de handoff:** `HO-AAAAMMDD-<workstream>-HHMM`.
- `<workstream>` = label corto kebab-case del tema de la sesión.
- `HHMM` = hora estimada de cierre.
- Si colisiona (mismo workstream, mismo minuto): añadir letra → `...-1834b`.
- Verificar unicidad escaneando los códigos existentes en el archivo antes de fijarlo.

## Alcance

Esta skill SOLO gestiona cierre y relevo. NO audita código. NO genera ni modifica
`AUDIT_LOG.md` (solo lo lee para cross-reference si existe). Si la sesión requiere
auditoría técnica, ejecútala con la skill correspondiente ANTES de invocar `/handoff`.

## Disparadores

- **Cierre (default):** `/handoff` · "cierra la sesión" · "guarda el progreso" ·
  "termina la sesión" · "haz el handoff" · "vamos a cerrar" · "session closure" · "wrap up".
- **Recepción:** `/handoff resume [código]` · "retoma la sesión" · "continúa el workstream X" ·
  "relevo de handoff".
- **Purga:** `/handoff purge [código]` · "limpia handoffs consumidos".

**NO disparar ante:** "guarda esto" / "termina esto" (tarea puntual) · "salir" / "adiós"
(despedida casual) · cualquier frase ambigua. Ante duda, preguntar antes de ejecutar.

---

# MODO CIERRE — `/handoff`

Ejecutar en orden estricto. No saltar pasos.

### Paso 1 — Recolección de datos

Recolectar de la conversación de la sesión:

- **Workstream:** label corto del tema de esta sesión (ej: `landing`, `proveedor-pms`). Si no es
  obvio, inferirlo y confirmarlo con el usuario. Va en el código del handoff.
- **Objetivo declarado:** ¿Qué se buscaba lograr? (1-2 líneas)
- **Plan original referenciado:** Título exacto y/o archivo del plan. Si no hubo, "Sin plan formal previo".
- **Fases completadas:** Número, descripción y resultado (completada / con desviaciones / parcial / abortada).
- **Archivos creados, modificados, eliminados:** Rutas completas. Para modificados, una línea del cambio.
- **Decisiones técnicas tomadas:** Con justificación (por qué, no solo qué).
- **Bugs detectados:** Si `AUDIT_LOG.md` existe y fue actualizado, listar por clasificación y cross-reference por fecha.
- **Deuda técnica generada:** Shortcuts, workarounds, TODOs intencionales.
- **Blockers externos activos:** Lo que bloquea continuar y no depende de Claude. Sección distinta de deuda técnica.
- **Estado del repo:** rama, último commit (7 chars), último zip entregado (si aplica).

Dato no verificable desde la conversación → marcarlo `[no verificado]` o `N/A`. No inventar.

### Paso 2 — Estimación de timestamps

```
Inicio aproximado: HH:MM [estimado]
Cierre aproximado: HH:MM [estimado]
Duración estimada: Xh Ym [estimado]
```

El sufijo `[estimado]` es obligatorio. Si son críticos (facturación, auditoría), advertir
en chat que son aproximados y deben verificarse contra el historial real.

### Paso 3 — Append a `sprint_report.md`

Localizar `sprint_report.md` en la raíz del proyecto.

- **Re-leer el archivo del disco AHORA**, justo antes de escribir. NO reconstruir el archivo
  desde tu contexto/memoria: una sesión hermana pudo haber añadido una entrada después de tu
  última lectura, y reconstruir desde memoria la borraría (lost-update).
- **Append literal al final.** Editar añadiendo tu entrada después de la última existente.
  NUNCA reescribir el archivo entero. NO modificar, reordenar ni resumir entradas previas.
- Si no existe: crear con header inicial + primera entrada.
- Usar `templates/sprint_report_entry.md`. Cada sección obligatoria; si no aplica, "N/A".
- **La entrada lleva su código de handoff** (`HO-AAAAMMDD-<workstream>-HHMM`, el mismo del
  Paso 4). Esto enlaza la entrada del log con la sección de `SESSION_HANDOFF.md` y permite
  que `resume` salte al detalle exacto.

### Paso 4 — Insertar sección en `SESSION_HANDOFF.md`

Localizar `SESSION_HANDOFF.md` en la raíz del proyecto.

1. **Si no existe:** crear con el header del registro (ver template) + tu sección 🟢.
2. **Si existe pero NO tiene ninguna sección `## (🟢|✅) HO-`** (formato legacy, snapshot
   viejo): su contenido previo es un handoff sin codificar. Convertirlo en **una** sección
   🟢 con código `HO-AAAAMMDD-legacy-HHMM` bajo el header nuevo. NO descartar ese contenido.
3. **Generar el código** `HO-AAAAMMDD-<workstream>-HHMM` (verificar unicidad).
4. **Colapsar a tombstone** las secciones ✅ que sigan con cuerpo completo (su detalle ya
   vive en `sprint_report.md` por código). Comprimir a una línea:
   `## ✅ HO-... — <workstream> · consumido AAAA-MM-DD · detalle en sprint_report.md`.
   No las borres aquí — eso es trabajo de `purge`.
5. **Insertar tu sección 🟢 nueva** usando `templates/session_handoff_section.md`.

**PROHIBIDO el overwrite total del archivo.** Las únicas operaciones legales sobre
`SESSION_HANDOFF.md` son: insertar una sección 🟢 nueva, colapsar/transicionar una sección
por su código, o (en modo purge) borrar secciones ✅. NUNCA tocar una sección 🟢 ajena.

### Paso 5 — Generar bloque de relevo en chat

Bloque de código (```) listo para pegar en una sesión nueva. Debe:

- Empezar con el **código del handoff** y la línea exacta: `/handoff resume <código>`.
- Ser autosuficiente: contexto mínimo del proyecto, stack, estado actual, siguiente paso concreto.
- Indicar archivos a leer: `SESSION_HANDOFF.md` (esta sección por su código),
  `AUDIT_LOG.md` (si existe), entrada de `sprint_report.md` (por el mismo código).
- Incluir advertencias activas: workarounds, decisiones a no revertir, blockers externos.
- Estar en español, salvo que el proyecto sea en otro idioma.

### Paso 6 — Confirmación en chat

- Resumen ejecutivo de 3-5 líneas: workstream cerrado, código asignado, archivos clave, blockers.
- Confirmar los tres artefactos con rutas, e indicar que la sección se insertó (no sobrescribió).
- El bloque de relevo dentro de triple backtick.
- Mencionar cualquier dato `[estimado]` o `[no verificado]`.

---

# MODO RECEPCIÓN — `/handoff resume [código]`

Relevo: una sesión nueva reclama un handoff vivo.

- **Sin código:** leer `SESSION_HANDOFF.md`, listar todas las secciones 🟢 con su workstream
  y siguiente-paso en una línea. Preguntar cuál retomar. No marcar nada todavía.
- **Con código:**
  1. Localizar la sección por su código.
  2. Si no existe o ya está ✅: avisar claramente. NO alucinar contenido, NO inventar un handoff.
  3. Volcar el detalle completo de la sección como contexto de arranque de la nueva sesión.
  4. Leer también la entrada de `sprint_report.md` con ese código y `AUDIT_LOG.md` si existe.
  5. **Marcar la sección 🟢 → ✅ y colapsar su cuerpo a tombstone** de una línea:
     `## ✅ HO-... — <workstream> · consumido AAAA-MM-DD · detalle en sprint_report.md`.

Una sección solo se consume cuando alguien leyó su contenido de verdad. Si no la vas a
volcar, NO la marques ✅.

---

# MODO PURGA — `/handoff purge [código]`

- Borra secciones **✅** del `SESSION_HANDOFF.md`. Sin código → todas las ✅. Con código → solo esa.
- **JAMÁS toca una sección 🟢.** Si el código apunta a una 🟢, rechazar y explicar que primero
  debe consumirse con `resume`.

---

## Reglas duras

1. **No inventar datos.** Métricas, líneas, porcentajes, timestamps exactos. Si no se midió, no se reporta. Si se estima, se etiqueta.
2. **No omitir secciones.** Si no aplica, "N/A". Formato consistente entre sesiones, no negociable.
3. **`sprint_report.md` es append-only literal.** Re-leer fresco + append al final. Nunca reescribir el archivo entero ni resumir entradas previas.
4. **`SESSION_HANDOFF.md` nunca se sobrescribe completo.** Solo insertar sección 🟢, transicionar/colapsar por código, o borrar ✅ en purge.
5. **Una sección 🟢 es intocable** salvo el `resume` que la marca ✅. Cerrar una sesión NUNCA toca el handoff vivo de otro workstream.
6. **Cada cierre = código único.** Nunca reusar un código vivo.
7. **`purge` jamás borra 🟢.**
8. **No ejecutar auditoría.** Si el usuario la espera dentro del handoff, recordar que son skills distintos.
9. **No tocar `AUDIT_LOG.md`.** Solo lectura para cross-reference.
10. **Trazabilidad de plan obligatoria.** Cada fase referencia su plan origen (título y/o archivo) o declara "Sin plan formal".

## Racionalizaciones prohibidas

Capturadas en testing baseline. Si te descubres pensando alguna, PARA y sigue la regla.

| Excusa | Realidad |
|--------|----------|
| "SESSION_HANDOFF es el git status / un snapshot único, así que lo sobrescribo" | Ya NO. Es un registro aditivo de handoffs vivos. El snapshot único era el bug. |
| "El estado de la otra sesión no se pierde, queda en git history" | **Falso.** La sesión receptora NO lee git history; lee `SESSION_HANDOFF.md`. Y el archivo puede no estar commiteado al cierre. Overwrite = pérdida real. |
| "Se consolidará cuando esa sesión haga su propio /handoff" | Eso es su append a `sprint_report`, no su relevo. Si borraste su sección 🟢, su siguiente-paso y advertencias ya se perdieron. |
| "La consigna era cerrar solo lo mío, y la skill mandaba overwrite" | Cerrar lo tuyo = insertar TU sección. Tocar lo ajeno (overwrite) es lo contrario de "solo lo mío". |
| "Marco la sección como consumida aunque no la volqué, para limpiar" | Consumir sin volcar = pérdida silenciosa. Solo `resume` que vuelca el detalle puede marcar ✅. |
| "Reconstruyo sprint_report completo desde mi contexto, es más limpio" | Tu contexto está stale. Una sesión hermana pudo escribir después. Re-leer + append literal. |

## Red flags — PARA

- Estás por hacer `Write` del archivo `SESSION_HANDOFF.md` completo → es overwrite, prohibido. Usa edición de sección.
- Estás por borrar o editar una sección 🟢 que no es la que estás consumiendo → prohibido.
- Estás justificando una pérdida con "git history" o "se consolidará después" → señal de overwrite encubierto.
- Vas a marcar ✅ algo que no volcaste → pérdida silenciosa.
- Vas a reconstruir `sprint_report.md` desde memoria en vez de re-leer el disco → lost-update.

## Integración con otras skills

- **`phased-approval`:** se invoca DESPUÉS de ejecutar un plan aprobado. No reemplaza la aprobación.
- **`execution-rules`:** cierra lo que `execution-rules` ejecutó; hereda contexto de fases.
- **`zip-versioning` / `zip-changelog` / `zip-completeness`:** si la sesión produjo zip(s), la sección registra la versión del último zip.
- **`AUDIT_LOG.md` (prompt separado):** cross-reference, sin ejecutar auditoría.
- **`no-yesman`:** no maquilla resultados. Sesión parcial o con desviaciones se reporta como tal.

## Errores comunes a evitar

- Sobrescribir `SESSION_HANDOFF.md` completo → destruye handoffs vivos de sesiones hermanas. El bug que esta skill existe para impedir.
- Generar una sección sin estado git/zip → la sesión receptora no sabe dónde está el código.
- Confundir deuda técnica con blockers externos.
- Inventar timestamps "exactos" sin `[estimado]`.
- Saltar el bloque de chat porque "ya está en el archivo" → el usuario lo pidió para portabilidad.
- Listar fases sin referenciar plan origen → trazabilidad rota a los 3 meses.
- Marcar ✅ un handoff sin haberlo volcado → relevo fantasma.
