# Handoff

> Skill de **cierre y relevo de sesión multi-workstream** para [Claude Code](https://claude.com/claude-code).
> Session closure & handoff skill for parallel workstreams.

Cuando corres **varias sesiones de Claude Code en paralelo sobre el mismo proyecto**
(ej. una en `landing`, otra en `proveedor-pms`, otra en `onboarding`), el cierre de sesión
tradicional sobrescribe un único archivo de handoff y **destruye el relevo que una sesión
hermana todavía no retomó**. Esta skill convierte ese archivo en un **registro aditivo de
handoffs vivos**: cada cierre inserta su propia sección codificada y nada vivo se
sobrescribe jamás.

---

## El problema

Un `SESSION_HANDOFF.md` tratado como *snapshot sobrescribible* funciona con una sola
sesión. Con varias en paralelo, cada cierre pisa al anterior y se pierde estado intermedio
(siguiente paso, advertencias, blockers) de workstreams que aún no se habían relevado.

## La solución

`SESSION_HANDOFF.md` deja de ser un snapshot y pasa a ser un **registro de handoffs vivos**:

```
🟢 vivo  ──/handoff resume <código>──▶  ✅ consumido (tombstone)  ──/handoff purge──▶  (borrado)
```

- Cada handoff es una **sección con código único** (`HO-AAAAMMDD-<workstream>-HHMM`) y estado.
- Varios handoffs de distintos workstreams **coexisten** en el archivo.
- Una sección 🟢 es **intocable** salvo por el `resume` que la transiciona a ✅.
- Borrar solo es legal sobre secciones ✅.

## Los tres modos

| Modo | Disparador | Qué hace |
|------|-----------|----------|
| **Cierre** (default) | `/handoff`, "cierra la sesión", "haz el handoff", "wrap up" | Append a `sprint_report.md` + inserta sección 🟢 codificada en `SESSION_HANDOFF.md` + genera bloque de relevo en chat. **Nunca sobrescribe** secciones de otros workstreams. |
| **Recepción** | `/handoff resume [código]`, "retoma la sesión", "continúa el workstream X" | Vuelca el detalle del handoff como contexto de arranque y lo marca ✅ (tombstone). |
| **Purga** | `/handoff purge [código]`, "limpia handoffs consumidos" | Borra secciones ✅. **Jamás toca una 🟢.** |

## Artefactos que produce

1. **`sprint_report.md`** — Append-only. Historial acumulativo de todas las sesiones. El `git log` del proyecto.
2. **`SESSION_HANDOFF.md`** — Registro de handoffs vivos (el corazón de la skill).
3. **Bloque de relevo en chat** — Copy-paste autosuficiente para arrancar una sesión nueva, con el código del handoff para reclamarlo sin abrir archivos.

## Instalación

Copia la carpeta dentro de tus skills de Claude Code:

```bash
git clone https://github.com/PieroJF/claude-handoff-skill.git ~/.claude/skills/handoff
```

O, si ya tienes el repo en otro sitio, copia el directorio:

```bash
cp -r claude-handoff-skill ~/.claude/skills/handoff
```

Claude Code detecta la skill por el frontmatter de `SKILL.md`. Invócala con `/handoff`.

## Uso

```text
# Cerrar la sesión actual (workstream landing)
/handoff

# Retomar un handoff vivo
/handoff resume HO-20260529-landing-1834

# Listar handoffs vivos (sin código)
/handoff resume

# Limpiar handoffs ya consumidos
/handoff purge
```

## Estructura

```
.
├── SKILL.md                              # Definición de la skill (frontmatter + lógica de los 3 modos)
├── templates/
│   ├── session_handoff_section.md        # Header del registro + plantilla de sección 🟢
│   └── sprint_report_entry.md            # Plantilla de entrada del sprint report
├── README.md
└── LICENSE
```

## Reglas duras (resumen)

- `SESSION_HANDOFF.md` **nunca se sobrescribe completo**: solo insertar sección 🟢, transicionar por código (🟢→✅) o borrar ✅.
- `sprint_report.md` es **append-only**: re-leer del disco y añadir al final, nunca reconstruir desde memoria.
- **No inventar datos**: lo no medido no se reporta; lo estimado se etiqueta `[estimado]`.
- Una sección solo se marca ✅ **cuando alguien volcó su contenido de verdad**.
- La skill **no audita código** ni toca `AUDIT_LOG.md` (solo lectura para cross-reference).

## Licencia

[MIT](LICENSE)
