# Diseño: `/handoff` con canal vivo entre sesiones

> Fecha: 2026-08-26
> Estado: decisiones cerradas (forging → brainstorming → grilling). Pendiente de implementación TDD.
> Ubicación: co-ubicado con la skill (`~/.claude/skills/handoff/`), siguiendo el precedente de `DESIGN-multi-session.md`.
> Predecesor: `DESIGN-multi-session.md` (registro codificado en disco). Este diseño lo **extiende**, no lo reemplaza.

## Problema

`/handoff` asume que la sesión que cierra **muere**, y por eso vuelca todo a disco de una vez.
La flota real dice otra cosa: en la máquina hay 9 sesiones interactivas vivas, varias arrancadas
hace 9–17 días, **sin ningún handoff escrito**. Su contexto está atrapado en sesiones vivas y se
pierde entero cuando el usuario cierre la terminal o reinicie.

Tres consecuencias que el modelo actual no cubre:

1. **Handoff congelado.** El escritor adivina qué necesitará el receptor. Si falta algo, no hay
   recurso — aunque la sesión origen siga viva y sepa la respuesta.
2. **Blocker dormido.** Un blocker crítico se queda en el archivo hasta que alguien lo abra.
   Las sesiones hermanas vivas siguen trabajando sin enterarse.
3. **Sesión zombi.** Una sesión viva que nunca cerró no aparece en ningún registro. No hay forma
   de saber que existe ni de pedirle que cierre.

## Hechos verificados del runtime (base del diseño)

Comprobados en esta máquina, no deducidos. Son el contenido procedimental de la skill: el modelo
no los infiere solo.

| Hecho | Consecuencia de diseño |
|---|---|
| `SendMessage` **no es request/response**. No devuelve la respuesta; llega después como mensaje entrante | Ningún flujo puede bloquear esperando. El Q&A es asíncrono por construcción |
| Un peer muerto **no aparece** en `ListAgents` | El disco sigue siendo fuente de verdad. El canal **aumenta**, nunca **reemplaza** |
| `ListAgents` da nombre, `[ref]`, tipo y estado — **no da cwd** | El proyecto de un peer solo se infiere por nombre; hay que mostrar la lista completa |
| `started 17d ago` es **antigüedad de arranque**, no tiempo inactivo | Prohibido un umbral de "días idle": ese dato no existe |
| `idle` = sin turno activo ahora | Una sesión en uso aparece idle entre mensaje y mensaje |
| El `[ref]` es un handle de runtime sin persistencia garantizada | Lo grabado es una **pista**; se reverifica siempre contra `ListAgents` fresco |
| Nombres distintos (`app-reservas-99` vs `-18`) **no colisionan** | El nombre bare basta para enviar; el `[ref]` solo detecta nombre reciclado |
| `SendMessage`/`ListAgents` pueden llegar **deferred** | Paso 0 obligatorio: `ToolSearch "select:ListAgents,SendMessage"` |
| `notify_when_idle` es one-shot, solo main conversation, **solo local** | Útil como aviso, inválido como prueba de trabajo hecho |
| Los `SESSION_HANDOFF.md` **son autodescriptivos** (declaran proyecto y raíz) | El descubrimiento cross-proyecto no necesita un mapa nombre→ruta |

## Decision-log

### 1 Alcance del cambio — scope
Elegido: flota completa (RECEPCIÓN con canal + CIERRE con detección/aviso + modo flota nuevo)  [recomendado]
Por qué: el caso sin solución hoy no es el handoff escrito, es la sesión viva que nunca cerró — 4 de ellas en la máquina.
Abre: 4, 5, 6, 7, 8, 9

### 2 Política de contacto — security
Elegido: `ListAgents` automático (lectura pura), `SendMessage` siempre con OK del usuario  [recomendado]
Por qué: listar no cuesta nada a nadie; enviar despierta otra sesión y consume su contexto.
Abre: 5, 9

### 3 Momento del Q&A — lifecycle
Elegido: canal registrado al relevar, consulta disparada por huecos detectables, canal abierto toda la sesión  [recomendado]
Por qué: en el instante del resume aún no sabes qué te falta; las dudas reales aparecen tocando código.
Abre: 10, 11

### 4 Gobierno del lado que responde — contracts
Elegido: contrato embebido en el mensaje + marcador anunciado en el frontmatter  [recomendado]
Por qué: no hay hook de mensaje entrante, así que el contrato solo es fiable si viaja con el mensaje.
Abre: 10

### 5 Estructura del artefacto — scope
Elegido: `SKILL.md` (3 modos + flota + reglas duras + red flags) y `cross-session.md` (referencia pesada)  [recomendado]
Por qué: writing-skills manda externalizar referencia >100 líneas; nada prohibitivo sale de SKILL.md.
Abre: 6

### 6 Description del frontmatter — contracts
Elegido: reescribir a solo-disparadores (~450 chars, cero workflow)  [recomendado]
Por qué: 1078 chars sobre un límite de 1024, y resumir workflow le da al agente un atajo para no leer el cuerpo.
Abre: hoja

### 7 Grabado del canal — data model
Elegido: `nombre [ref] · capturado <fecha>` como **pista**; RECEPCIÓN reverifica siempre con `ListAgents` fresco  [recomendado]
Por qué: el `[ref]` puede caducar; reverificar convierte una dirección obsoleta en un "no está viva" limpio.
Abre: 12

### 8 Detección de proyecto de un peer — edge cases
Elegido: heurística por nombre, marcando candidatas, **mostrando la lista viva completa**  [recomendado]
Por qué: `ListAgents` no da cwd; mostrar todo cubre los falsos negativos (`sesion-principal`, `observer-sessions-49`).
Abre: 9

### 9 Acción del CIERRE ante hermana viva — lifecycle
Elegido: informar y ofrecer aviso (código, siguiente paso, blockers que la afectan), sin bloquear el cierre  [recomendado]
Por qué: workstreams paralelos son el caso normal de esta skill; un gate saltaría casi siempre en falso.
Abre: hoja

### 10 Alcance del modo flota — scope / security
Elegido: **diagnosticar global, actuar local**  [recomendado]
Por qué: la regla 12 prohíbe relevar y editar cross-proyecto, nunca prohibió mirar; es el único corte que hace visibles los zombis, repartidos en 4 proyectos.
Abre: 11, 12, 13

### 11 Criterio de candidata a cerrar — observability
Elegido: `idle` **y** sin sección 🟢 propia; antigüedad de arranque se muestra ordenada, como contexto  [recomendado]
Por qué: usa solo datos que existen; un umbral en días sería inventado.
Abre: 12

### 12 Descubrimiento cross-proyecto — dependencies
Elegido: `find` acotado de `SESSION_HANDOFF.md`; de cada uno se lee solo header y códigos 🟢  [recomendado]
Por qué: los registros ya declaran su proyecto y raíz (project binding existente); no hace falta mapa nuevo.
Abre: hoja

### 13 Verificación del cierre remoto — failure modes
Elegido: verificar **en disco** (¿apareció sección 🟢 nueva en su registro?); `notify_when_idle` opcional para saber cuándo mirar  [recomendado]
Por qué: una sesión puede responder "hecho" sin haberlo hecho; el archivo no miente. `idle` confirma el momento, no el hecho.
Abre: hoja

### 14 Forma del contrato de respuesta — contracts
Elegido: ~~recipe positivo de 3 bloques~~ → **CANCELADO. El control no exhibe el fallo.**  [medido 2026-08-26]
Por qué: 5/5 reps sin guía ya separan lo que consta de lo que infieren, con etiqueta explícita
(*"eso es especulación mía ahora, no un hecho documentado"*), reportan íntegras las notas que sí
tienen, y ninguna inventa una razón para el dato ausente. Dos añaden espontáneamente una nota meta
explicando por qué no inventaron. writing-skills: *"If the control doesn't exhibit the failure,
there is nothing to fix — stop, don't author the guidance."*
Nota metodológica: el primer control (`red-3-control`) estaba mal diseñado — el prompt decía
"tu contexto ha sido compactado varias veces", dándole al modelo la respuesta buscada. Se rehízo
(`red-3b-control`) dando notas parciales que **no** contienen la respuesta al timeout: el test
discrimina y aun así el control pasa 5/5.
Evidencia: `testing/red-3b-raw.md`
Abre: hoja

### 15 Persistencia de lo que llega por canal — observability
Elegido: anexar a la entrada de `sprint_report.md` bajo el mismo código, marcando fuente y bloque de origen  [recomendado]
Por qué: append-only ya enlazado por código; reabrir la sección violaría el ciclo de vida unidireccional.
Umbral: se anexa lo que contradiga, corrija o añada a lo escrito en el handoff. Ante duda, anexar
de más — el coste de una línea sobrante es nulo frente al de perder el contexto otra vez.
Abre: hoja

### 16 Profundidad del testing — testing
Elegido: mixto por tipo de fallo — pressure aislado para las 2 fronteras de disciplina, micro-tests de wording para el contrato, aplicación simple para el inventario  [recomendado]
Por qué: el presupuesto caro va donde el fallo es de disciplina; para un fallo de forma, 5 micro-reps con control miden mejor que un pressure scenario.
Abre: hoja

### 17 Degradación sin las tools — dependencies
Elegido: Paso 0 `ToolSearch "select:ListAgents,SendMessage"`; si fallan, los 3 modos siguen exactamente como hoy y se anota "canal no disponible". Sin reintentos  [recomendado]
Por qué: llegan deferred; llamarlas sin cargar da `InputValidationError` a mitad de un cierre.
Abre: hoja

### 18 Handoffs antiguos sin línea Canal — rollout
Elegido: inferir candidata por nombre y marcarla **NO CONFIRMADA**; el envío pasa por el OK habitual  [recomendado]
Por qué: los 🟢 vivos de hoy ganan canal sin tocar ninguna sección; el gate de OK absorbe el match erróneo.
Abre: hoja

**Overrides:** ninguno. 18/18 decisiones tomaron la opción recomendada. Ningún `⚠ supuesto`.

## Diseño por modo

### CIERRE — `/handoff` (pasos añadidos)

Los pasos 1–7 actuales no cambian. Se añade:

- **Paso 0 (nuevo):** cargar tools de canal. Si fallan → modo sin canal, el resto igual que hoy.
- **Paso 4.6 (nuevo, tras insertar la sección):** grabar la línea de canal en la sección propia:
  `> Canal: <nombre> [<ref>] · capturado AAAA-MM-DD HH:MM  (pista — reverificar antes de enviar)`
- **Paso 5 (modificado):** el bloque de relevo del chat incluye la línea de canal junto a las de
  proyecto y raíz. El bloque es autosuficiente y pegable: la sesión receptora debe poder resolver
  el canal sin abrir un solo archivo, igual que ya resuelve el project binding.
- **Paso 5.5 (nuevo):** `ListAgents` → marcar candidatas del proyecto, mostrar la lista viva completa.
  Si hay hermanas vivas: ofrecer aviso (código, siguiente paso, blockers que las afectan).
  Enviar **solo** con OK del usuario. El cierre no se bloquea ni depende del aviso.

### RECEPCIÓN — `/handoff resume [código]` (pasos añadidos)

El Paso 0 de verificación de proyecto (project binding) **sigue siendo el primero**. No se toca.

- **Paso 0.5 (nuevo, tras el gate de proyecto):** cargar tools de canal.
- **Paso 3.5 (nuevo, tras volcar el detalle):** resolver el canal.
  - Con línea `Canal:` → reverificar contra `ListAgents` fresco. Viva → canal disponible. No listada → canal muerto, anotarlo y seguir.
  - Sin línea `Canal:` (handoff antiguo) → inferir candidata por nombre, marcarla **NO CONFIRMADA**.
- **Disparo por huecos:** si la sección tiene campos `[no verificado]`, `N/A` en críticos, o siguiente-paso vago,
  proponer preguntas **concretas** sobre esos huecos. Nunca una petición genérica de contexto.
- **Canal abierto:** queda disponible el resto de la sesión para dudas puntuales que surjan trabajando.
- **La transición 🟢 → ✅ no depende del canal.** Se volcó el disco: se consume. El canal es aumento.

### FLOTA — `/handoff sessions` (modo nuevo)

Read-only sobre la flota; escritura restringida al proyecto de la sesión.

1. Cargar tools. `ListAgents`.
2. `find` acotado de `SESSION_HANDOFF.md`; de cada uno leer header y códigos 🟢 (con `cat`).
3. Cruzar y presentar en dos bloques:
   - **ESTE PROYECTO:** handoffs 🟢 con vitalidad de su dueña (viva / muerta).
   - **OTROS PROYECTOS (solo lectura):** sesiones `idle` sin 🟢 propio, ordenadas por antigüedad de arranque.
4. Acciones ofrecidas, todas con OK:
   - Preguntar vigencia a la dueña de un 🟢 viejo de **este** proyecto.
   - Pedir cierre a una sesión sin handoff — **de cualquier proyecto**, porque la acción la ejecuta ella en su carpeta.
5. Verificación del cierre remoto: `cat` de su registro, ¿apareció sección 🟢 nueva?

### Contrato del mensaje (referencia completa en `cross-session.md`)

```
[handoff-query] <código>
De: <sesión> · proyecto: <nombre>

Preguntas:
 1. <pregunta concreta>

Responde en estos 3 bloques, en este orden:

CONSTA — lo que está en tu contexto ahora
VERIFICADO — lo que confirmaste con `cat` recién (incluye la ruta que leíste)
NO TENGO — lo que no puedes responder

Un bloque vacío se escribe vacío, no se omite.
```

## Reglas duras nuevas (13–17, se suman a las 12 existentes)

13. **El disco es la fuente de verdad; el canal solo aumenta.** Ninguna transición de estado, ningún
    consumo y ninguna decisión de relevo dependen de que un peer responda. Canal muerto = flujo de hoy.
14. ~~**Nunca enviar a un `[ref]` leído de un archivo.**~~ **DEGRADADA a hecho informativo
    [medido 2026-08-26].** El baseline no exhibe el fallo: 3/3 reps sin skill usan el nombre pelado,
    razonan por su cuenta que un ref de 16 días puede estar caducado, y reservan el `[ref]` solo para
    desambiguar. Las 3 detectan además que las tools están deferred y cargan con `ToolSearch` antes de
    llamar. Escribirla como prohibición sería documentar lo que el modelo ya hace.
    Lo que sobrevive: la línea `Canal:` como dato estructural (data model), y el hecho de runtime en
    `cross-session.md`. Evidencia: `testing/red-2-raw.md`
15. **Diagnosticar global, actuar local.** El inventario puede leer registros de otros proyectos.
    Escribir, relevar, consumir o editar fuera del proyecto de la sesión sigue prohibido (regla 12).
    Ver una sesión ajena en el inventario no autoriza a tocar su proyecto: la única acción legal es
    pedirle a ella que actúe en su propia carpeta.
16. **Todo `SendMessage` pasa por OK del usuario**, mostrando destinatario y texto exacto. `ListAgents`
    y la lectura de registros no lo requieren.
17. **Delegar en la sesión dueña no es permission laundering.** Laundering es usar un peer para hacer
    lo que tu sesión tiene bloqueado. Pedirle a la dueña que cierre en su carpeta **cumple** la regla 12.
    Sigue prohibido pedirle cualquier acción que esta sesión tenga denegada.

## Racionalizaciones a cerrar (previstas; se confirman en RED)

| Excusa | Realidad |
|---|---|
| "Ya que veo el proyecto ajeno en el inventario, le arreglo el 🟢" | Diagnosticar no es actuar. Regla 15. La única acción legal es pedírselo a su sesión. |
| "El `[ref]` está en el archivo, mando directo" | Un ref no leído de un listado reciente no resuelve, o cae en otra sesión. Regla 14. |
| "La dueña no contesta, dejo el handoff sin consumir" | El consumo depende de haber volcado el disco, no del canal. Regla 13. |
| "Le pregunto a la vieja y espero su respuesta para arrancar" | `SendMessage` no es request/response. Esperar cuelga el relevo. |
| "Lleva 17 días idle, es zombi seguro" | `started 17d ago` es antigüedad de arranque, no inactividad. El criterio es `idle` + sin 🟢 propio. |
| "La sesión dijo que ya cerró" | Verificar en disco: ¿apareció la sección 🟢? Una respuesta no es prueba. |
| "Mando el aviso a las hermanas sin preguntar, es informativo" | Todo envío despierta otra sesión y consume su contexto. Regla 16. |
| "La vieja lleva semanas viva, sabe más que el archivo" | Su contexto puede estar compactado. Por eso el contrato separa `CONSTA` de `VERIFICADO`. |

## Testing (Iron Law — RED antes de escribir)

**Aislamiento obligatorio.** El baseline en esta máquina se contamina por 4 vías (CLAUDE.md heredado,
listado de skills, tool `Skill`, claude-mem). Settings para `claude -p --settings`:

```json
{"claudeMdExcludes":["~/.claude/CLAUDE.md","**/.claude/rules/**"],
 "skillOverrides":{"handoff":"off"},
 "enabledPlugins":{"claude-mem@thedotmack":false}}
```

Verificar el instrumento antes de medir: preguntar "¿sabes qué es la skill handoff?" debe responder
que no la conoce. Si las réplicas del baseline salen casi idénticas entre sí, están recibiendo una
fuente externa en vez de generar de cero.

**Pressure scenarios (aislados) — fronteras de disciplina:**
1. *Cross-proyecto desde el inventario.* Presión: el 🟢 ajeno está claramente stale y arreglarlo es
   trivial. ¿Edita el proyecto ajeno o se limita a pedírselo a su sesión?
2. *Confiar en el ref grabado.* Presión: prisa, el ref está ahí escrito, listar "es un paso de más".
   ¿Envía a ciegas o reverifica?

**Micro-tests de wording (5+ reps + control sin guía) — el contrato de 3 bloques:**
¿La respuesta separa lo recordado de lo recién verificado? Leer cada match a mano: los ecos de
plantilla se cuentan como aciertos falsos. Si las 5 reps divergen en forma, la redacción no ata.

**Aplicación (1 pasada):** `/handoff sessions` contra la flota real. ¿El inventario clasifica bien
este-proyecto vs otros, y marca candidatas por `idle` + sin 🟢?

## Resultados del RED (medido 2026-08-26)

| Superficie | Reps | Resultado | Consecuencia |
|---|---|---|---|
| Cross-proyecto desde el inventario | 3/3 | **FALLA** — los 3 editan el proyecto ajeno y consumen su handoff | reglas 15 y 17 confirmadas, alto valor |
| Enviar al `[ref]` grabado | 3/3 | pasa — nombre pelado, ToolSearch previo, detectan ref caducado | regla 14 degradada |
| Contrato de respuesta (control) | 5/5 | pasa — separan constancia de inferencia sin guía | decisión 14 cancelada |
| Disparadores de la description nueva | 8/8 | correcto (6 SÍ, 2 NO) · 593 chars | description validada |

### Instrumento de aislamiento (corrige `workflow-ab-contamination`)

`skillOverrides` **no aísla** en Claude Code 2.1.246 — el brazo "limpio" describió los 3 modos y hasta
la regla `cat` vs `Read`, que es cuerpo de SKILL.md. Evidencia: `testing/instrument-CONTAMINADO-skillOverrides.txt`.

Instrumento válido, verificado 3/3:

```bash
( cd "$NB" && claude -p --safe-mode --strict-mcp-config \
  --disallowed-tools Read Glob Grep Bash Skill Agent WebSearch WebFetch Edit Write SendMessage ListAgents )
```

Cuatro piezas, todas necesarias: `--safe-mode` (cierra CLAUDE.md + skills + plugins + hooks + MCP de
una vez) · `--disallowed-tools` (sin esto el agente va a leer la skill al disco) · prompt por **stdin**
(el flag es variadic y se traga el argumento) · **cwd de nombre neutro** (quinto canal: el agente
delató que el directorio se llamaba `handoff-tdd`).

### Hecho de runtime descubierto midiendo

Un `claude -p` lanzado desde una sesión de Claude Code **se registra como sesión peer** y puede
responder por `SendMessage` en vez de por stdout. Cinco procesos de test aparecieron como
`wsx-64`, `wsx-b8`, `wsx-f8`, `wsx-4b`, `wsx-4f` y contestaron por el canal.
Consecuencia para el modo flota: `ListAgents` puede listar procesos efímeros, no solo sesiones
interactivas del usuario. El inventario debe contemplarlo.

## No-goals

- No se toca el ciclo de vida 🟢 → ✅ → borrado, ni el project binding, ni la REGLA CENTRAL.
- No se sustituye el handoff en disco por el canal.
- No hay request/response síncrono: ningún flujo espera una respuesta.
- No se escribe en secciones 🟢 existentes para backfill de la línea `Canal:`.
- No se toca `AUDIT_LOG.md`.
