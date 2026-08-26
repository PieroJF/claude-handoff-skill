# Canal vivo entre sesiones — referencia

> Consultivo. Las prohibiciones y reglas duras viven en `SKILL.md`, no aquí.
> Medido 2026-08-26. Evidencia en `testing/`.

## Hechos del runtime

No se deducen: se midieron. Un diseño que los ignore falla en silencio.

| Hecho | Consecuencia |
|---|---|
| `SendMessage` **no es request/response**. No devuelve la respuesta; llega después como mensaje entrante | Ningún flujo puede bloquear esperando. El Q&A es asíncrono por construcción |
| Un peer muerto **no aparece** en `ListAgents` | El disco es la fuente de verdad. El canal aumenta, nunca reemplaza |
| `ListAgents` da nombre, `[ref]`, tipo y estado — **no da cwd** | El proyecto de un peer solo se infiere por nombre. Mostrar siempre la lista completa |
| `started 17d ago` es antigüedad de **arranque**, no tiempo inactivo | No existe el dato "días sin actividad". Un umbral en días sería inventado |
| `idle` = sin turno activo ahora mismo | Una sesión en uso aparece `idle` entre mensaje y mensaje |
| El `[ref]` es un handle de runtime sin persistencia garantizada | Lo grabado es pista. El nombre pelado es la dirección; el `[ref]` solo desambigua |
| Nombres distintos (`app-reservas-99` vs `-18`) **no colisionan** | El `[ref]` hace falta solo si dos filas comparten nombre exacto |
| `SendMessage` / `ListAgents` pueden llegar **deferred** | Cargar con `ToolSearch "select:ListAgents,SendMessage"` antes de usarlas |
| `notify_when_idle` es one-shot, solo main conversation, **solo local** | Sirve para saber cuándo mirar. No prueba que el trabajo se hiciera |
| Los `SESSION_HANDOFF.md` **declaran su proyecto y raíz** | El descubrimiento cross-proyecto no necesita un mapa nombre→ruta |
| Un `claude -p` lanzado desde una sesión **se registra como peer** y puede responder por `SendMessage` | `ListAgents` puede listar procesos efímeros, no solo sesiones del usuario. No todo lo listado es una sesión de trabajo |

## Formato del mensaje de consulta

Identificación + preguntas concretas. Nada más: medido que el lado que responde ya separa por su
cuenta lo que le consta de lo que infiere, y lo etiqueta (`testing/red-3b-raw.md`, 5/5 sin guía).

```
[handoff-query] <código>
De: <sesión> · proyecto: <nombre>

 1. <pregunta concreta sobre un hueco del handoff>
 2. <otra>
```

Las preguntas salen de huecos **detectables** en la sección: campos `[no verificado]`, `N/A` en algo
crítico, siguiente-paso vago. Una petición genérica de contexto devuelve lo que ya está en el archivo.

## Formato del inventario de flota

```
ESTE PROYECTO (<nombre>)
  🟢 HO-20260825-landing-1834 · landing · dueña viva (sesion-principal, idle)
  🟢 HO-20260814-proveedor-pms-1620 · proveedor-pms · dueña MUERTA

OTROS PROYECTOS (solo lectura · idle y sin 🟢 propio)
  app-reservas-99 [6a13cc] · arrancó 17d
  tesis-13  [b0faaf] · arrancó 12d
  → única acción posible: pedirles que cierren en su carpeta

(`idle` = sin turno activo ahora, no = días sin actividad)
```

## Formato del aviso a hermanas al cerrar

```
HO-20260825-landing-1834 cerrado (workstream landing).
Blocker que te afecta: API proveedor-pms caída desde las 14:00 — no toques src/booking/.
Siguiente paso registrado: reactivar el retry cuando responda.
Detalle: /handoff resume HO-20260825-landing-1834
```

## Formato del bloque de rescate en `sprint_report.md`

```markdown
#### Rescatado por canal · AAAA-MM-DD HH:MM
Fuente: <sesión>
> <lo que aportó, citado>
```

Se anexa lo que contradiga, corrija o añada a lo escrito en el handoff. Ante duda, anexar de más:
una línea sobrante no cuesta nada; perder el contexto otra vez, sí.

## Tabla de fallos del canal

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `InputValidationError` al llamar `ListAgents` o `SendMessage` | tool deferred, esquema sin cargar | `ToolSearch "select:ListAgents,SendMessage"` |
| El nombre no resuelve | sesión muerta, o nombre reciclado por una más nueva | canal muerto: seguir con disco, anotarlo |
| Error pidiendo desambiguar | dos filas con el mismo nombre exacto | añadir el ` [ref]` del listado **recién leído** |
| No llega respuesta | peer `busy`, o ignoró el mensaje | no reintentar, no bloquear. El relevo no depende de ello |
| Aparecen sesiones que no reconoces | procesos `claude -p` efímeros registrados como peers | no son sesiones de trabajo: no pedirles cierre |

## Instrumento de aislamiento para testear esta skill

`skillOverrides` **no aísla** en 2.1.246 (medido: el brazo "limpio" describió los 3 modos y la regla
`cat` vs `Read`). El que sí funciona, verificado 3/3:

```bash
( cd "$DIR_NEUTRO" && claude -p --safe-mode --strict-mcp-config \
  --disallowed-tools Read Glob Grep Bash Skill Agent WebSearch WebFetch Edit Write SendMessage ListAgents )
```

Las cuatro piezas son necesarias: `--safe-mode` cierra CLAUDE.md + skills + plugins + hooks + MCP de
una vez · `--disallowed-tools` evita que el agente lea la skill del disco · el prompt va por **stdin**
porque el flag es variadic y se traga el argumento · el cwd necesita **nombre neutro**, porque un
directorio llamado `handoff-tdd` ya es una pista y el agente lo dijo.
