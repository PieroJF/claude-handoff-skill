---
name: handoff
description: Use when el usuario invoca `/handoff`, `/handoff resume`, `/handoff purge` o `/handoff sessions`, o usa frases inequívocas de cierre ("cierra la sesión", "guarda el progreso", "termina la sesión", "haz el handoff", "vamos a cerrar", "wrap up"), de relevo ("retoma la sesión", "continúa el workstream X", "relevo de handoff"), de limpieza ("limpia handoffs consumidos") o de flota ("qué sesiones tengo abiertas", "sesiones sin cerrar", "inventario de sesiones"). NO usar para auditorías de código ni ante frases ambiguas como "guarda esto" o "termina esto" referidas a tareas puntuales.
---

# Skill: Handoff — Cierre, Relevo y Flota de Sesiones

## Propósito

Esta skill gestiona el cierre y relevo de sesiones de trabajo en proyectos donde el
usuario corre **varias sesiones en paralelo sobre distintos workstreams** (ej: `landing`,
`proveedor-pms`, `onboarding`). Produce y mantiene tres artefactos:

1. **`sprint_report.md`** — Append-only. Historial acumulativo de TODAS las sesiones del
   proyecto. Responde "¿qué hicimos en esta sesión?". Es el `git log`.
2. **`SESSION_HANDOFF.md`** — **Registro de handoffs vivos**, NO un snapshot sobrescribible.
   Cada handoff es una sección con código único y estado (`[closed-pending] 🟢` vivo / `[closed] ✅` consumido). Varios
   handoffs de distintos workstreams coexisten. Responde "¿qué relevos hay pendientes y
   cómo se retoma cada uno?".
3. **Bloque de relevo en chat** — Copy-paste inmediato para arrancar una sesión nueva.
   Lleva el código del handoff para que la sesión receptora lo reclame sin abrir archivos.

Y gestiona un cuarto elemento que **no** es un artefacto en disco: el **canal vivo**. Las sesiones
de esta máquina se ven entre sí (`ListAgents`) y pueden hablarse (`SendMessage`). Eso permite
preguntarle a la sesión que escribió un handoff, avisar a las hermanas vivas al cerrar, e inventariar
sesiones que nunca cerraron. **El canal aumenta al disco; jamás lo reemplaza:** un peer muerto no
aparece, y ningún flujo de esta skill depende de que alguien conteste.
Formatos, hechos de runtime y tabla de fallos: `cross-session.md` (co-ubicado).

## Por qué cambió el modelo (NO lo ignores)

`SESSION_HANDOFF.md` **dejó de ser un snapshot que se sobrescribe**. Antes, cada cierre
sobrescribía el archivo completo. Con varias sesiones en paralelo eso **destruía** el
handoff que una sesión hermana aún no había retomado (caso real documentado: 4 overwrites
en un día, estado intermedio perdido). El modelo nuevo es **aditivo y codificado**: cada
cierre inserta su propia sección con código único; nada vivo se sobrescribe jamás.

## Modelo de datos — `SESSION_HANDOFF.md`

```markdown
# SESSION_HANDOFF — <proyecto>
> Registro de handoffs. [closed-pending] 🟢 vivo = sesión cerrada, aún no relevada ·
> [closed] ✅ consumido = sesión cerrada y relevada, purgable.
> Reclamar: /handoff resume <código>   ·   Limpiar: /handoff purge

## [closed-pending] 🟢 HO-20260529-landing-1834 — landing
> Proyecto: sitio-web · raíz: /home/usuario/proyectos/sitio-web
> Canal: sesion-principal [c7cf27] · capturado 2026-05-29 18:34  (pista — reverificar antes de enviar)
（detalle completo del handoff: ver template de sección）

## [closed-pending] 🟢 HO-20260529-proveedor-pms-1620 — proveedor-pms
（detalle completo…）

## [closed] ✅ HO-20260528-onboarding-2210 — onboarding · consumido 2026-05-29 · detalle en sprint_report.md
```

**Etiqueta de estado en el nombre.** El header de cada sección lleva una etiqueta de texto
**pareada con el emoji**: `[closed-pending]` acompaña a 🟢 (la sesión que generó el handoff
ya cerró, pero el relevo aún no se recibió) y `[closed]` acompaña a ✅ (la sesión cerró y el
handoff se relevó con éxito en una sesión nueva). El emoji es la **fuente canónica** de
estado; la etiqueta es su **alias en texto** (grepeable). Transicionan **siempre juntos**.

**Ciclo de vida (unidireccional):**

```
[closed-pending] 🟢 vivo  ──/handoff resume <código>──▶  [closed] ✅ consumido (tombstone)  ──/handoff purge──▶  (borrado)
```

**REGLA CENTRAL (no negociable):** borrar o reescribir una sección SOLO es legal si está
`[closed] ✅`. Una sección `[closed-pending] 🟢` es **intocable**, salvo por el `resume` que la transiciona a `[closed] ✅`.

**Código de handoff:** `HO-AAAAMMDD-<workstream>-HHMM`.
- `<workstream>` = label corto kebab-case del tema de la sesión.
- `HHMM` = hora estimada de cierre.
- Si colisiona (mismo workstream, mismo minuto): añadir letra → `...-1834b`.
- Verificar unicidad escaneando los códigos existentes en el archivo antes de fijarlo.
- La etiqueta de estado (`[closed-pending]` / `[closed]`) se antepone al **header** de la
  sección y **no** forma parte del código. El `resume` localiza por código, no por etiqueta.

## El registro puede estar versionado — entonces hay uno por RAMA

`SESSION_HANDOFF.md` suele estar **trackeado en git** (medido: lo está en `servicio-bot` y
`app-reservas`; no en `PANEL-V5`). Donde lo está, no existe "el registro del proyecto":
existe **un registro por rama**, y dos sesiones en ramas distintas ven estados distintos sin
saberlo. Medido en `servicio-bot`: `main` y `chore/upgrade-framework` con 6 tombstones,
`fix/firma-por-tenant` con 5.

**Antes de consumir en cualquier proyecto, comprobar dos cosas:**

```bash
git ls-files --error-unmatch SESSION_HANDOFF.md   # ¿trackeado?
git branch --show-current                          # ¿en qué rama estás?
```

- **No trackeado** → el registro es del working tree. Sin problema de ramas. Sigue.
- **Trackeado y estás en `main`** → lo normal. Sigue.
- **Trackeado y estás en una rama de feature** → tus tombstones viven **solo en esa rama**.
  `main` seguirá mostrando esas secciones 🟢, y otra sesión puede consumirlas otra vez → doble
  consumo y conflicto al mergear. Deja el cambio del registro en un **commit propio y separado**
  del trabajo de la rama, para poder cherry-pickearlo a `main` sin arrastrar nada más.

**Nunca cambies de rama para arreglar esto.** Varias sesiones comparten un working tree y un solo
HEAD: un `git checkout` le mueve el suelo a quien esté trabajando ahí. Si hace falta otra rama,
es un `git worktree` — y aun así, los contenedores y redes de Docker cuelgan del compose de la
carpeta original, así que un worktree sirve para editar archivos, no para levantar el stack.

## Vínculo de proyecto (project binding) — aislamiento cross-proyecto

Cada handoff está **atado a un proyecto concreto**: la **carpeta raíz** donde viven su
`SESSION_HANDOFF.md` y su `sprint_report.md` (ej. `/home/usuario/proyectos/sitio-web`). Esa
**raíz canónica** (ruta absoluta) se graba en dos sitios: en la sección del handoff dentro
de `SESSION_HANDOFF.md` y en el **bloque de relevo del chat**. Es parte obligatoria del
handoff, no decorativa.

**Por qué importa (no lo ignores):** el bloque de relevo es **autosuficiente y pegable en
CUALQUIER sesión** — incluida una abierta en la carpeta equivocada. Un handoff de un proyecto
ejecutado desde la sesión de otro es un desastre silencioso: se carga el `project-context`
equivocado, los backups (`backup-before-modify`) van a otro repo, y se crean o editan archivos
en el proyecto ajeno. Por eso la sesión receptora, **antes de volcar contexto o tocar nada**,
verifica que su carpeta actual **es** la raíz del proyecto del handoff (o está dentro de ella).
Si no coincide: **parada en seco**, sin consumir el handoff, para que se releve en la carpeta
correcta (ver MODO RECEPCIÓN, Paso 0 — Verificación de proyecto).

## Alcance

Esta skill SOLO gestiona cierre, relevo y diagnóstico de flota. NO audita código. NO genera ni
modifica `AUDIT_LOG.md` (solo lo lee para cross-reference si existe). Si la sesión requiere
auditoría técnica, ejecútala con la skill correspondiente ANTES de invocar `/handoff`.

**Límite del canal vivo:** el inventario de flota **lee** de toda la máquina, pero esta skill solo
**escribe** en el proyecto de la sesión actual. Ver un handoff ajeno en el inventario no autoriza a
tocarlo (regla dura 15).

## Disparadores

- **Cierre (default):** `/handoff` · "cierra la sesión" · "guarda el progreso" ·
  "termina la sesión" · "haz el handoff" · "vamos a cerrar" · "session closure" · "wrap up".
- **Recepción:** `/handoff resume [código]` · "retoma la sesión" · "continúa el workstream X" ·
  "relevo de handoff".
- **Purga:** `/handoff purge [código]` · "limpia handoffs consumidos".
- **Flota:** `/handoff sessions` · "qué sesiones tengo abiertas" · "sesiones sin cerrar" ·
  "inventario de sesiones".

**NO disparar ante:** "guarda esto" / "termina esto" (tarea puntual) · "salir" / "adiós"
(despedida casual) · cualquier frase ambigua. Ante duda, preguntar antes de ejecutar.

---

# Lectura de archivos vivos — OBLIGATORIO `cat`, NUNCA el tool `Read`

`SESSION_HANDOFF.md`, `sprint_report.md` y `AUDIT_LOG.md` se leen **SIEMPRE con `Bash cat`**
(o `sed -n 'A,Bp'` para un rango), **nunca con el tool `Read`**.

**Por qué (no lo ignores):** el plugin **claude-mem** engancha un `PreToolUse` sobre `Read` y, para
archivos > 1500 B que ya indexó — justo estos, leídos sesión tras sesión — fuerza la lectura real a
`limit: 1` e inyecta un **resumen stale** de una sesión anterior. Crees que releíste el disco y
recibiste 1 línea más una versión vieja: exactamente el lost-update que esta skill existe para
impedir. `cat` no matchea ese hook. **No "optimices" esto de vuelta a `Read`.**

**Para ESCRIBIR** con el tool `Edit`, su guard exige un `Read` previo que te llegará truncado. No es
problema: `Edit` aplica contra el disco real, no contra la vista truncada. Receta: (1) `cat` para la
verdad; (2) un `Read` desechable solo para desbloquear `Edit`, **ignora lo que muestre**; (3) `Edit`
con `old_string`/`new_string` construidos desde el `cat`. Para `sprint_report.md`, al ser append-only,
usa `printf '%s' "…" >> archivo` y sáltate `Edit`.

---

# MODO CIERRE — `/handoff`

Ejecutar en orden estricto. No saltar pasos.

### Paso 0 — Cargar el canal (si está disponible)

`ListAgents` y `SendMessage` pueden llegar **deferred**: llamarlas sin cargar da `InputValidationError`
a mitad del cierre. Cargarlas primero:

```
ToolSearch "select:ListAgents,SendMessage"
```

Si no cargan: **modo sin canal**. Los pasos 1–7 siguen exactamente igual que siempre, se anota
`Canal: no disponible` en la sección, y no se reintenta. El cierre a disco nunca depende del canal.

### Paso 1 — Recolección de datos

Recolectar de la conversación de la sesión:

- **Proyecto y raíz canónica:** nombre del proyecto + **ruta absoluta de su carpeta raíz**
  (donde viven `SESSION_HANDOFF.md` / `sprint_report.md`). Obtenerla con `pwd` (o la raíz del
  repo git). Es el **vínculo de proyecto**: se graba en la sección y en el bloque de relevo, y
  la sesión receptora la usa para verificar que se reanuda en la carpeta correcta (Paso 0 de
  RECEPCIÓN). Sin este dato el handoff no es relevable de forma segura.
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

- **Re-leer el archivo del disco AHORA con `cat`** (no el tool `Read` — ver "Lectura de archivos
  vivos"; `Read` te daría 1 línea + un resumen stale de claude-mem, que es indistinguible de no
  releer), justo antes de escribir. NO reconstruir el archivo desde tu contexto/memoria: una
  sesión hermana pudo haber añadido una entrada después de tu última lectura, y reconstruir desde
  memoria la borraría (lost-update).
- **Append literal al final.** Editar añadiendo tu entrada después de la última existente.
  NUNCA reescribir el archivo entero. NO modificar, reordenar ni resumir entradas previas.
- Si no existe: crear con header inicial + primera entrada.
- Usar `templates/sprint_report_entry.md`. Cada sección obligatoria; si no aplica, "N/A".
- **La entrada lleva su código de handoff** (`HO-AAAAMMDD-<workstream>-HHMM`, el mismo del
  Paso 4). Esto enlaza la entrada del log con la sección de `SESSION_HANDOFF.md` y permite
  que `resume` salte al detalle exacto.

### Paso 4 — Insertar sección en `SESSION_HANDOFF.md`

Localizar `SESSION_HANDOFF.md` en la raíz del proyecto y **leerlo con `cat`** (no el tool `Read`
— ver "Lectura de archivos vivos"; truncado a 1 línea podrías no detectar secciones existentes,
clasificar mal un archivo como legacy, o sobrescribir handoffs vivos ajenos).

1. **Si no existe:** crear con el header del registro (ver template) + tu sección `[closed-pending] 🟢`.
2. **Si existe pero NO tiene ninguna sección que matchee `## (\[closed(-pending)?\] )?(🟢|✅) HO-`**
   (formato legacy, snapshot viejo): su contenido previo es un handoff sin codificar. Convertirlo
   en **una** sección `[closed-pending] 🟢` con código `HO-AAAAMMDD-legacy-HHMM` bajo el header
   nuevo. NO descartar ese contenido.
   **Y crea también su entrada en `sprint_report.md` con ese mismo código**, con el cuerpo legacy
   dentro. Si no, esa sección queda sin detalle al que apuntar y el `resume` que la consuma
   producirá un tombstone huérfano.
   **La detección se ancla en el emoji (🟢|✅) y tolera la etiqueta de texto opcional antes de él.**
   Un archivo cuyas secciones ya llevan `[closed-pending]`/`[closed]` NO es legacy — nunca lo
   re-envuelvas.
3. **Generar el código** `HO-AAAAMMDD-<workstream>-HHMM` (verificar unicidad).
4. **Colapsar a tombstone** las secciones `[closed] ✅` que sigan con cuerpo completo (su detalle ya
   vive en `sprint_report.md` por código). Comprimir a una línea:
   `## [closed] ✅ HO-... — <workstream> · consumido AAAA-MM-DD · detalle en sprint_report.md`.
   No las borres aquí — eso es trabajo de `purge`.
5. **Insertar tu sección `[closed-pending] 🟢` nueva** usando `templates/session_handoff_section.md`.
   La sección **debe** llevar la línea de **vínculo de proyecto** (`> Proyecto: <nombre> · raíz:
   <ruta-absoluta>`) justo bajo el header. Sin ella el handoff no se puede verificar al relevar.
6. **Grabar el canal.** Debajo del vínculo de proyecto, la identidad de esta sesión tal como la
   imprime `ListAgents` (la primera línea de su salida dice cómo se llama esta sesión):
   `> Canal: <nombre> [<ref>] · capturado AAAA-MM-DD HH:MM  (pista — reverificar antes de enviar)`
   Es una **pista para buscar**, no una dirección para enviar: el `[ref]` es un handle de runtime que
   puede caducar. Si el canal no está disponible: `> Canal: no disponible`. El campo se escribe
   siempre, no se omite.

**PROHIBIDO el overwrite total del archivo.** Las únicas operaciones legales sobre
`SESSION_HANDOFF.md` son: insertar una sección `[closed-pending] 🟢` nueva, colapsar/transicionar
una sección por su código (🟢→✅, moviendo etiqueta y emoji juntos), o (en modo purge) borrar
secciones `[closed] ✅`. NUNCA tocar una sección `[closed-pending] 🟢` ajena.

### Paso 5 — Generar bloque de relevo en chat

Bloque de código (```) listo para pegar en una sesión nueva. Debe:

- Empezar con el **código del handoff** y la línea exacta: `/handoff resume <código>`.
- Declarar el **vínculo de proyecto** en sus primeras líneas, explícito y visible:
  `Proyecto: <nombre>` y `Raíz del proyecto: <ruta-absoluta>`. Esto permite que la sesión
  receptora detecte de inmediato si fue pegado en la carpeta equivocada y se pare en seco.
- Incluir la línea `Canal: <nombre> [<ref>]`. El bloque es autosuficiente: la sesión receptora debe
  poder resolver el canal sin abrir un archivo, igual que ya resuelve el vínculo de proyecto.
- Ser autosuficiente: contexto mínimo del proyecto, stack, estado actual, siguiente paso concreto.
- Indicar archivos a leer: `SESSION_HANDOFF.md` (esta sección por su código),
  `AUDIT_LOG.md` (si existe), entrada de `sprint_report.md` (por el mismo código).
- Incluir advertencias activas: workarounds, decisiones a no revertir, blockers externos.
- Estar en español, salvo que el proyecto sea en otro idioma.

### Paso 5.5 — Avisar a las sesiones hermanas vivas

Solo si el canal está disponible. **No bloquea el cierre.**

1. `ListAgents`. Marcar como candidatas del proyecto las sesiones cuyo nombre matchee el nombre del
   proyecto o de su carpeta raíz — `ListAgents` **no da cwd**, así que es heurística, no dato.
2. **Mostrar la lista viva completa**, no solo las que matchean: `sesion-principal` u `observer-sessions-49`
   no delatan su proyecto por el nombre, y el usuario sí sabe cuáles son suyas. Marcar aparte los
   procesos efímeros si los hubiera (un `claude -p` lanzado desde una sesión aparece como peer).
3. Si hay hermanas vivas, **ofrecer** enviarles un aviso: código del handoff, siguiente paso, y los
   blockers que las afectan. Formato en `cross-session.md`.
4. **Enviar solo con el OK explícito del usuario**, mostrando destinatario y texto exacto. Un envío
   despierta esa sesión y consume su contexto; no es una lectura gratis.
5. Si el usuario dice que no, o nadie contesta: seguir. El cierre ya está en disco.

Workstreams paralelos son el caso **normal** de esta skill. Esto es un aviso, no un gate: no detengas
el cierre porque haya otra sesión viva en el proyecto.

### Paso 6 — Confirmación en chat

- Resumen ejecutivo de 3-5 líneas: workstream cerrado, código asignado, archivos clave, blockers.
- Confirmar los tres artefactos con rutas, e indicar que la sección se insertó (no sobrescribió).
- El bloque de relevo dentro de triple backtick.
- Mencionar cualquier dato `[estimado]` o `[no verificado]`.

### Paso 7 — Tag de cierre en el selector `/resume` (manual, cosmético)

El título que `/resume` muestra **no lo controla esta skill**. Para que la sesión cerrada aparezca
tageada, **imprime al usuario esta línea lista para pegar** (Claude no puede ejecutar slash-commands):

```
/rename [closed] <workstream>
```

- `<workstream>` = el mismo label del código del handoff.
- Se tagea directo `[closed]`, no `[closed-pending]`: el usuario hace el `/rename` una sola vez al
  cerrar y nunca vuelve al selector a subirlo, así que `[closed-pending]` quedaría stale para siempre.
- **Eje distinto al de `SESSION_HANDOFF.md`:** en el título `[closed]` solo significa *sesión cerrada*;
  en el registro significa *relevado*, y solo lo pone un `resume` que volcó el contenido. El estado
  canónico vive en el registro, nunca en el título.

---

# MODO RECEPCIÓN — `/handoff resume [código]`

Relevo: una sesión nueva reclama un handoff vivo.

### Paso 0 — Verificación de proyecto (GATE — antes de TODO lo demás)

**Esto corre PRIMERO, antes de localizar la sección, antes de volcar contexto, antes de tocar
un solo archivo.** El handoff está atado a un proyecto (su raíz canónica — ver "Vínculo de
proyecto"). Una sesión solo puede relevar handoffs **de su propio proyecto**.

1. **Determinar la raíz del proyecto del handoff.** Tomarla del bloque de relevo pegado en el
   chat (línea `Raíz del proyecto: <ruta>`) y/o de la línea `> Proyecto: … · raíz: …` de la
   sección en `SESSION_HANDOFF.md`.
2. **Determinar la carpeta actual de la sesión:** `pwd` (o la raíz del repo git actual).
3. **Comparar.** La sesión es válida solo si su carpeta actual **es** la raíz del handoff o
   **está dentro** de ella. (Workstreams distintos del mismo proyecto comparten raíz → válido.)
4. **Si NO coincide → PARADA EN SECO. Negarse a continuar.**
   - **NO** volcar el contexto del handoff. **NO** empezar el trabajo descrito. **NO** leer ni
     editar archivos de ningún proyecto. **NO** resolver el código contra el `SESSION_HANDOFF.md`
     de otra carpeta ni ir a buscarlo a otros directorios.
   - **NO** transicionar la sección a `[closed] ✅`. El handoff queda **intacto y vivo**
     (`[closed-pending] 🟢`) para que la sesión correcta lo releve.
   - Decir al usuario, claro y corto: este handoff pertenece a `<proyecto>` (raíz `<ruta>`); la
     sesión actual está en `<pwd>`; **abre una sesión en `<ruta>` y ahí ejecuta
     `/handoff resume <código>`**. No se hizo ningún cambio.
   - Aunque el bloque de relevo se anuncie "autosuficiente", eso **no** autoriza a ejecutarlo en
     la carpeta equivocada: autosuficiente = no necesita abrir archivos para el contexto, **no** =
     puede correr en cualquier proyecto.
5. **Si coincide:** continuar con el flujo normal (abajo).

Solo si el Paso 0 pasa, proceder:

- **Sin código:** leer `SESSION_HANDOFF.md` **con `cat`** (no el tool `Read` — ver "Lectura de
  archivos vivos"; truncado verías solo la primera línea y no listarías ningún handoff vivo, o
  alucinarías a partir del resumen stale), listar todas las secciones `[closed-pending] 🟢` con su
  workstream y siguiente-paso en una línea. Preguntar cuál retomar. No marcar nada todavía.
- **Con código:**
  1. Localizar la sección por su código.
  2. Si no existe o ya está `[closed] ✅`: avisar claramente. NO alucinar contenido, NO inventar un handoff.
  3. Volcar el detalle completo de la sección como contexto de arranque de la nueva sesión.
  4. Leer también (con `cat`, no `Read`) la entrada de `sprint_report.md` con ese código y `AUDIT_LOG.md` si existe.
  4.5 **Comprobar que el tombstone apuntará a algo real.** El tombstone dice "detalle en
     `sprint_report.md`", así que antes de colapsar: `grep <código> sprint_report.md`.
     **Si no hay entrada** — típico de las secciones migradas desde formato legacy por el Paso 4.2
     de CIERRE, que crea la sección pero no su entrada — **añade primero el cuerpo literal de la
     sección a `sprint_report.md`** (append, sin tocar nada previo) y colapsa después. Colapsar sin
     esto deja un tombstone que apunta a un detalle inexistente: el contenido se pierde de verdad,
     que es exactamente lo que esta skill existe para impedir. Medido en `servicio-bot`:
     `HO-20260517-legacy-1720` tenía 0 coincidencias en `sprint_report.md`.
  5. **Transicionar la sección `[closed-pending] 🟢 → [closed] ✅` (etiqueta y emoji a la vez) y
     colapsar su cuerpo a tombstone** de una línea:
     `## [closed] ✅ HO-... — <workstream> · consumido AAAA-MM-DD · detalle en sprint_report.md`.
  6. **Resolver el canal vivo** (opcional, nunca bloqueante). Cargar tools con
     `ToolSearch "select:ListAgents,SendMessage"`; si no cargan, terminar aquí.
     - **Con línea `Canal:`** → correr `ListAgents` **fresco** y buscar tanto por `[ref]` como por
       nombre. **Ninguno de los dos es estable en el tiempo** (medido dos veces, en direcciones
       opuestas: un día cambian los nombres conservando el ref; tres días después un nombre
       sobrevive apuntando a una sesión **distinta**). Si el handoff tiene más de unas horas,
       **confirma la identidad preguntando** antes de tratarla como la dueña — una sesión que
       heredó el nombre dirá que no conoce ese código. Si no aparece o no lo confirma: canal
       muerto, se anota y se sigue. Lo grabado es pista, no dirección.
     - **Sin línea `Canal:`** (handoff anterior a este formato) → buscar en `ListAgents` una sesión
       cuyo nombre matchee el proyecto y ofrecerla marcada **NO CONFIRMADA**: puede no ser la que
       escribió el handoff. Nunca se rellena esa línea en la sección ajena (regla dura 5).
     - **MEDIR el siguiente-paso antes de tratarlo como pendiente.** Un handoff declara el estado
       del día en que se cerró, no el de hoy: el trabajo pudo hacerse después sin que nadie volviera
       a tocar la sección. Antes de trasladar un pendiente a `PENDIENTES.md` o de arrancarlo,
       compruébalo contra el código — que el archivo exista, que la función esté, que el commit sea
       ancestro de la rama. **Medido dos veces en el mismo proyecto:** un plan de 9 tareas declarado
       pendiente estaba entero en producción, y un cluster de 8 secciones declaraba trabajo que ya
       llevaba dos meses en `main`. Copiar un siguiente-paso sin medirlo produce un documento que
       nace mintiendo, y alguien reconstruye lo que ya existe.
     - **Preguntar solo por huecos concretos:** campos `[no verificado]`, `N/A` en algo crítico,
       siguiente-paso vago. Una petición genérica de contexto devuelve lo que ya está en el archivo.
       Enviar solo con OK del usuario. Formato en `cross-session.md`.
     - Lo que llegue por canal y **contradiga, corrija o añada** a lo escrito: anexarlo a la entrada
       de `sprint_report.md` de ese código. Si se queda en el chat, se pierde con esta sesión.

**La transición a `[closed] ✅` NO depende del canal.** Se volcó el disco: se consume. Canal muerto,
peer que no contesta o tools que no cargan no cambian nada del relevo.

Una sección solo se consume cuando alguien leyó su contenido de verdad. Si no la vas a
volcar, NO la transiciones a `[closed] ✅`.

---

# MODO FLOTA — `/handoff sessions`

Inventario de sesiones vivas cruzado con los handoffs pendientes. Responde: *¿qué sesiones tengo
abiertas, cuáles guardan contexto que se perdería, y qué handoffs 🟢 siguen esperando dueño?*

**Diagnostica global, actúa local.** Lee de toda la máquina; escribe solo en el proyecto de esta sesión.

1. **Cargar tools.** `ToolSearch "select:ListAgents,SendMessage"`. Si no cargan, este modo no puede
   operar: decirlo y parar. No hay fallback a disco para un inventario de sesiones vivas.
2. **`ListAgents`.** Anotar nombre, `[ref]`, tipo y estado de cada peer.
3. **Descubrir los registros.** `find` acotado de `SESSION_HANDOFF.md`, **sin rutas solapadas**:
   pasar `~/Desktop/claude` y `~/Desktop` a la vez duplica cada resultado. Usa la raíz mayor con
   `-maxdepth 4`, o `-prune`. **Las rutas llevan espacios** (`WORKSPACE28/SITIO-WEB-PROD`):
   usa `-print0` o `while read`, nunca `| xargs` a pelo — parte la ruta y ese registro desaparece
   del inventario en silencio. Medido: así se perdieron 8 secciones de un conteo. De cada registro, leer **con `cat`** solo su header y sus códigos 🟢.
   **Identifica cada registro por su RUTA, nunca por su nombre de proyecto.** Los worktrees declaran
   el mismo nombre que su repo padre — en esta máquina tres rutas distintas dicen `app-reservas` —
   así que agrupar por nombre mezcla registros que no tienen nada que ver.
   Anota además si cada registro está **trackeado en git** y en qué rama está su carpeta: donde lo
   está, el registro es por rama y el inventario de una rama de feature no representa a `main`.
4. **Cruzar y presentar en dos bloques** (formato en `cross-session.md`).
   **Cuenta primero, vuelca después.** Un proyecto puede acumular decenas de secciones 🟢 sin relevar
   (medido en esta máquina: 65 repartidas en 13 registros, hasta 12 en uno solo). Volcarlas todas
   convierte el inventario en ruido:
   - **ESTE PROYECTO:** total de 🟢 y, en detalle, **solo los 5 más recientes** por código, con la
     vitalidad de su dueña (viva / muerta) resuelta contra `ListAgents` fresco. Si hay más, decir
     cuántas quedan y ofrecer listarlas. Prioriza las de dueña viva: son las únicas consultables.
   - **OTROS PROYECTOS (solo lectura):** sesiones `idle` **y** sin sección 🟢 propia, ordenadas por
     antigüedad de arranque. Ese es el criterio: `idle` es estado real y "dejó handoff" es verificable
     en disco. **No existe el dato "días sin actividad"** — `started 17d ago` es cuándo arrancó, no
     cuánto lleva parada. Nunca marcar a nadie por días.
   - Si el total de 🟢 de este proyecto pasa de 10, decirlo como lo que es: un registro que nadie
     purga. Sugerir `resume` + `purge`, sin ejecutarlos por cuenta propia.
5. **Acciones ofrecidas, todas con OK del usuario:**
   - Preguntar vigencia a la dueña de un 🟢 viejo **de este proyecto**.
   - Pedir a una sesión **sin handoff** que cierre — de cualquier proyecto, porque **la ejecuta ella
     en su propia carpeta**. Esa es la única acción legal sobre un proyecto ajeno.
6. **Verificar un cierre remoto en disco, no por respuesta.** `cat` de su `SESSION_HANDOFF.md`:
   ¿apareció una sección 🟢 nueva? Una sesión puede contestar "hecho" sin haberlo hecho; el archivo no
   miente. `notify_when_idle` sirve para saber cuándo mirar, no como prueba.

**No todo lo listado es una sesión de trabajo.** Un `claude -p` lanzado desde otra sesión aparece
como peer. No pedirle cierre a un proceso efímero.

---

# MODO PURGA — `/handoff purge [código]`

- Borra secciones **`[closed] ✅`** del `SESSION_HANDOFF.md`. Sin código → todas las `[closed] ✅`.
  Con código → solo esa.
- **JAMÁS toca una sección `[closed-pending] 🟢`.** Si el código apunta a una `[closed-pending] 🟢`,
  rechazar y explicar que primero debe consumirse con `resume`.

---

## Reglas duras

1. **No inventar datos.** Métricas, líneas, porcentajes, timestamps exactos. Si no se midió, no se reporta. Si se estima, se etiqueta.
2. **No omitir secciones.** Si no aplica, "N/A". Formato consistente entre sesiones, no negociable.
3. **`sprint_report.md` es append-only literal.** Re-leer fresco + append al final. Nunca reescribir el archivo entero ni resumir entradas previas.
4. **`SESSION_HANDOFF.md` nunca se sobrescribe completo.** Solo insertar sección `[closed-pending] 🟢`, transicionar/colapsar por código, o borrar `[closed] ✅` en purge.
5. **Una sección `[closed-pending] 🟢` es intocable** salvo el `resume` que la transiciona a `[closed] ✅`. Cerrar una sesión NUNCA toca el handoff vivo de otro workstream.
6. **Cada cierre = código único.** Nunca reusar un código vivo.
7. **`purge` jamás borra `[closed-pending] 🟢`.**
8. **No ejecutar auditoría.** Si el usuario la espera dentro del handoff, recordar que son skills distintos.
9. **No tocar `AUDIT_LOG.md`.** Solo lectura para cross-reference.
10. **Trazabilidad de plan obligatoria.** Cada fase referencia su plan origen (título y/o archivo) o declara "Sin plan formal".
11. **Etiqueta y emoji son un token pareado.** El header de cada sección lleva `[closed-pending] 🟢` o `[closed] ✅`. La transición 🟢→✅ es **simultáneamente** `[closed-pending]`→`[closed]`: nunca muevas uno sin el otro. El emoji es la fuente canónica de estado; la etiqueta es su alias grepeable. La detección de secciones se ancla en el emoji y tolera la etiqueta opcional.
12. **Un handoff solo se releva en su propio proyecto.** En RECEPCIÓN, el Paso 0 verifica que la carpeta actual de la sesión es la raíz del proyecto del handoff. Si no coincide: parada en seco, sin volcar, sin tocar archivos, sin consumir; el handoff queda vivo (`[closed-pending] 🟢`) para la carpeta correcta. Cada cierre graba la raíz canónica en la sección y en el bloque de relevo (Reglas de CIERRE) — sin ese vínculo el handoff no es relevable de forma segura.

13. **El disco es la fuente de verdad; el canal solo aumenta.** Ninguna transición de estado, ningún
    consumo y ninguna decisión de relevo dependen de que un peer conteste. Sin canal, los tres modos
    de disco funcionan exactamente igual que antes de que existiera.
14. **Diagnosticar es global; actuar es local.** El inventario puede leer `SESSION_HANDOFF.md` de
    otros proyectos. Escribir, editar, relevar o consumir fuera del proyecto de esta sesión sigue
    prohibido (regla 12). **Ver un handoff ajeno no autoriza a tocarlo:** la única acción legal sobre
    otro proyecto es pedirle a **su** sesión que actúe en su propia carpeta.
15. **Todo `SendMessage` pasa por OK explícito del usuario**, mostrando destinatario y texto exacto.
    Un envío despierta esa sesión y consume su contexto. `ListAgents` y leer registros no lo requieren.
    **El OK va después de ver el texto, no antes.** Un "sí a todos" dado por adelantado aprueba la
    acción, no el contenido: enseña los mensajes y espera. Para un lote, basta un OK para el lote
    entero — enseñar los cuatro textos juntos y pedir una sola confirmación es correcto; enviarlos
    en el mismo turno en que se enseñan, no.
16. **Delegar en la sesión dueña no es permission laundering.** Laundering es usar un peer para hacer
    lo que tu sesión tiene bloqueado. Pedirle a la dueña que cierre en su carpeta **cumple** la regla
    12. Sigue prohibido pedirle cualquier acción que esta sesión tenga denegada.

## Racionalizaciones prohibidas

Capturadas en testing baseline. Si te descubres pensando alguna, PARA y sigue la regla.

| Excusa | Realidad |
|--------|----------|
| "SESSION_HANDOFF es el git status / un snapshot único, así que lo sobrescribo" | Ya NO. Es un registro aditivo de handoffs vivos. El snapshot único era el bug. |
| "El estado de la otra sesión no se pierde, queda en git history" | **Falso.** La sesión receptora NO lee git history; lee `SESSION_HANDOFF.md`. Y el archivo puede no estar commiteado al cierre. Overwrite = pérdida real. |
| "Se consolidará cuando esa sesión haga su propio /handoff" | Eso es su append a `sprint_report`, no su relevo. Si borraste su sección `[closed-pending] 🟢`, su siguiente-paso y advertencias ya se perdieron. |
| "La consigna era cerrar solo lo mío, y la skill mandaba overwrite" | Cerrar lo tuyo = insertar TU sección. Tocar lo ajeno (overwrite) es lo contrario de "solo lo mío". |
| "Marco la sección como consumida aunque no la volqué, para limpiar" | Consumir sin volcar = pérdida silenciosa. Solo `resume` que vuelca el detalle puede transicionar a `[closed] ✅`. |
| "Reconstruyo sprint_report completo desde mi contexto, es más limpio" | Tu contexto está stale. Una sesión hermana pudo escribir después. Re-leer + append literal. |
| "Actualizo el emoji de estado y la etiqueta `[closed...]` da igual / la actualizo después" | No. Etiqueta y emoji son un token pareado; desincronizarlos rompe el grep y confunde el estado. Muévelos juntos en la misma edición. |
| "El archivo no matchea `## (🟢|✅) HO-`, debe ser legacy, lo re-envuelvo" | Si las secciones llevan `[closed-pending]`/`[closed]` NO es legacy. La detección se ancla en el emoji y tolera la etiqueta. Re-envolver destruiría handoffs ya codificados. |
| "Ya leí el handoff con el tool `Read`, está fresco" | No. claude-mem intercepta `Read` y lo trunca a 1 línea + resumen stale para archivos > 1500 B que ya indexó. Lo que viste puede ser de una sesión anterior. Re-lee con `cat`. |
| "El bloque de relevo es autosuficiente, así que arranco el trabajo aquí mismo" | Autosuficiente = trae el contexto sin abrir archivos; NO = se puede ejecutar en cualquier carpeta. Si la raíz del handoff ≠ tu `pwd`, Paso 0 manda parada en seco. |
| "El handoff es de otro proyecto, pero abro/edito sus archivos desde esta sesión y listo" | Cross-proyecto silencioso: `project-context` equivocado, backups al repo equivocado, archivos ajenos tocados. Para en seco y dile al usuario que releve en la carpeta correcta. |
| "El código no está en mi `SESSION_HANDOFF.md`, voy a buscarlo en otras carpetas" | Prohibido. Un código solo se resuelve contra el proyecto de la sesión actual. Si no está aquí, es de otro proyecto → Paso 0, parada en seco. |
| "Lo marco consumido igual, total ya leí el bloque del chat" | Si la raíz no coincide no se consume nada: el handoff debe quedar vivo para la sesión correcta. Consumirlo aquí = relevo robado, lo pierde la carpeta dueña. |
| **"Es tu máquina, eres el único dev y me lo pides explícitamente, así que trabajar fuera de la raíz no es problema"** | Ser el único dev elimina el conflicto **entre personas**, no el desastre técnico: `project-context` equivocado, backups al repo equivocado, hooks del proyecto ajeno sin cargar. La regla 12 nació de eso, no de un choque de equipo. |
| **"Como mucho verás algún prompt de permisos por tocar archivos fuera del proyecto"** | El prompt de permisos autoriza **la escritura**, no verifica que sea el proyecto correcto. No es un guardián de aislamiento y no fue diseñado para serlo. |
| **"La sesión que lo escribió ya no existe, no hay riesgo de pisarle el trabajo a otro agente vivo"** | Que la dueña esté muerta es motivo para **no** tocar, no para tocar: nadie va a detectar tu error en ese repo. Ausencia de conflicto de escritura ≠ permiso para actuar cross-proyecto. |
| **"Todo es reversible vía git"** | Supone tres cosas no garantizadas: que commiteas, que el árbol estaba limpio, y que alguien mira. Ya está prohibida arriba para el overwrite; reaparece disfrazada de cruce de proyecto. |
| **"No toco nada más de ese repo, solo el fix y la entrada del handoff"** | Acotar el cruce no lo vuelve local. Un cruce pequeño carga el `project-context` equivocado igual que uno grande. |
| **"Los edits fuera de tu directorio te van a saltar como prompts de permiso, apruébalos y sigo"** | Delegar el guardián al usuario a las 2 AM es exactamente cuando no revisa. El gate es tuyo, no suyo. |
| "Uso `git -C otro-repo` sin cambiar mi cwd, así no cruzo de proyecto" | El cruce lo define **qué repo modificas**, no desde qué carpeta lanzas el comando. `git -C` es el cruce, no su mitigación. |
| "Espero a que la otra sesión conteste antes de arrancar" | `SendMessage` no es request/response: la respuesta llega en un turno posterior. Esperar cuelga el relevo, que ya tenía todo lo que necesitaba en disco. |
| "Lleva 17 días idle, es una sesión zombi" | `started 17d ago` es antigüedad de **arranque**, no inactividad. Pudo trabajar hace cinco minutos. El criterio es `idle` + sin 🟢 propio. |
| "Colapso a tombstone; el detalle queda en sprint_report" | Solo si esa entrada existe. Las secciones migradas desde legacy no la tienen: el tombstone apuntaría a nada. `grep` el código antes de colapsar. |
| "Consumo aquí y ya está, el registro es del proyecto" | Si está trackeado, el registro es **de la rama**. Comprueba `git ls-files` y en qué rama estás antes de consumir. |
| "Me cambio a main un momento para dejar el registro bien" | Comparten working tree y HEAD. Un `checkout` le mueve el suelo a la sesión que esté trabajando ahí — hay incidentes reales por esto. |
| "El envío falló con `No agent named X`, luego la sesión murió" | Puede haberse **renombrado**. Busca también por `[ref]` en un `ListAgents` fresco antes de darla por muerta. |
| "El handoff dice que esto queda pendiente, así que lo es" | Dice lo que quedaba pendiente **el día del cierre**. Mídelo contra el código antes de creerlo: medido, un plan de 9 tareas "pendiente" estaba entero en producción. |
| "Lo traslado a PENDIENTES tal cual, ya se verificará al ejecutarlo" | Un PENDIENTES que nace mintiendo hace reconstruir trabajo hecho. Verificar cuesta un `grep`; rehacer 9 tareas, no. |
| "El nombre coincide con el del handoff, así que es la dueña" | Los nombres se reciclan: medido, mismo nombre apuntando a una sesión distinta tres días después. Confírmalo preguntándole si conoce el código. |
| "La otra sesión dijo que ya cerró, lo doy por hecho" | Verificar en disco: ¿apareció la sección 🟢? Una respuesta no es prueba de trabajo hecho. |
| "El usuario ya dijo 'sí a todas', así que enseño los mensajes y los mando en el mismo turno" | Ese sí aprobó **la acción**, no **el texto** que aún no había leído. Enseña y espera. Un OK por lote vale; un OK anticipado al contenido, no. |

## Red flags — PARA

- Estás por hacer `Write` del archivo `SESSION_HANDOFF.md` completo → es overwrite, prohibido. Usa edición de sección.
- Vas a leer `SESSION_HANDOFF.md` / `sprint_report.md` / `AUDIT_LOG.md` con el tool `Read` → claude-mem lo trunca a 1 línea + resumen stale. Usa `cat`. Ver "Lectura de archivos vivos".
- Estás por borrar o editar una sección `[closed-pending] 🟢` que no es la que estás consumiendo → prohibido.
- Estás justificando una pérdida con "git history" o "se consolidará después" → señal de overwrite encubierto.
- Vas a transicionar a `[closed] ✅` algo que no volcaste → pérdida silenciosa.
- Vas a reconstruir `sprint_report.md` desde memoria en vez de re-leer el disco → lost-update.
- Vas a mover el emoji de estado sin mover su etiqueta de texto (o al revés) → desincronización del token pareado. Mueve `[closed-pending] 🟢` y `[closed] ✅` como una unidad.
- Vas a clasificar como legacy un `SESSION_HANDOFF.md` cuyas secciones ya llevan `[closed-pending]`/`[closed]` → la detección se ancla en el emoji y tolera la etiqueta; NO es legacy.
- Vas a volcar un handoff, abrir sus archivos o empezar su tarea **sin haber comparado su raíz de proyecto contra tu `pwd`** → corre el Paso 0 primero. Raíz ≠ `pwd` = parada en seco, sin consumir.
- Estás por relevar/editar archivos de un proyecto distinto al de tu carpeta actual → cross-proyecto prohibido. El handoff se releva en su propia carpeta.
- Viste un handoff ajeno en el inventario de flota y vas a **arreglarlo, aplicarlo o consumirlo** → diagnosticar no es actuar. Regla 14. La única acción legal es pedírselo a su sesión.
- Estás justificando un cruce con "soy el único dev", "es reversible", "solo toco dos líneas" o "saltará un prompt de permisos" → las cuatro están en la tabla de arriba. Para.
- Vas a llamar a `ListAgents` o `SendMessage` sin haberlas cargado con `ToolSearch` → `InputValidationError` a mitad del cierre.
- Vas a mandar un `SendMessage` sin enseñarle antes al usuario destinatario y texto → regla 15.
- Vas a bloquear un cierre o un relevo esperando que un peer conteste → el canal nunca es bloqueante.
- Vas a marcar una sesión como zombi por sus días de arranque → ese dato no mide inactividad.
- Vas a dar por cerrada una sesión remota porque contestó que sí → míralo en su registro.
- Vas a copiar un siguiente-paso a una lista de pendientes sin haberlo comprobado contra el código → mide primero; los handoffs envejecen y nadie vuelve a marcarlos.
- Vas a colapsar una sección sin haber comprobado que su código aparece en `sprint_report.md` → tombstone huérfano, pérdida real.
- Vas a consumir sin haber comprobado si el registro está trackeado y en qué rama estás → puedes estar escribiendo tombstones que `main` nunca verá.
- Vas a hacer `git checkout` en una carpeta que comparte working tree con otra sesión → prohibido; es un worktree o nada.
- Un envío falló y vas a concluir que la sesión murió → busca su `[ref]` en un listado fresco: lo normal es que se haya renombrado.

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
- Transicionar a `[closed] ✅` un handoff sin haberlo volcado → relevo fantasma.
