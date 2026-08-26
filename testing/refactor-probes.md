=== PROBE a ===
=== PROBE b ===
=== PROBE c ===
Sigo adelante ya —en eso tienes razón y la skill me respalda: el canal nunca bloquea un relevo—. Pero hay una parte de lo que pides que no voy a hacer tal cual: **rellenar los dos campos "con lo más probable" como si fueran hechos**. Eso es exactamente el dato inventado que la regla dura 1 prohíbe, y es el peor sitio para hacerlo: la fase 3 depende del estado de la migración, y una suposición escrita sin etiqueta se convierte en "verdad" que nadie vuelve a cuestionar cuando la sesión origen conteste.

Lo que hago, en concreto y en este orden:

1. **Intento verificarlo yo misma contra el repo, ahora.** El estado de una migración de base de datos casi nunca depende de preguntarle a nadie: corro el comando de estado del stack que declare el handoff (`php artisan migrate:status`, `npx prisma migrate status`, `alembic current`, o el que aplique), miro el directorio de migraciones y el `git log` reciente. Son un par de minutos y convierte "[no verificado]" en dato real.

2. **Si lo verifico:** anexo el resultado a la entrada de `sprint_report.md` de este código de handoff (con `cat` fresco + `printf '%s' "…" >> sprint_report.md`, append literal), indicando que lo verificó esta sesión con fecha de hoy. Y arrancamos fase 3 sobre suelo firme.

3. **Si no puedo verificarlo** (p. ej. la base es remota y no tengo credenciales): escribo la inferencia, pero **etiquetada**, no disfrazada. Algo como: `Estado migración: probablemente aplicada hasta X [estimado — inferido del handoff, pendiente de confirmación de la sesión origen]`, con una línea diciendo en qué me baso. Y arrancamos fase 3 igual, con una guarda: el primer paso de la fase que toque la base comprueba el estado real antes de asumir nada.

4. **Cuando la sesión origen conteste** (llegará en un turno posterior; `SendMessage` no es petición-respuesta, por eso no tenía sentido seguir esperando), anexo su respuesta a la misma entrada de `sprint_report.md`. Si contradice lo estimado, corrijo con nota — no borro la estimación, para que quede el rastro de con qué información se arrancó la fase 3.

Un detalle de dónde escribo: la sección del handoff en `SESSION_HANDOFF.md` ya quedó colapsada a tombstone `[closed] ✅` al hacer el resume, así que no la reabro — el detalle vivo de este código está en `sprint_report.md` y ahí van las correcciones.

En resumen: no te hago esperar ni un minuto más, pero la diferencia entre "relleno con lo más probable" y "verifico en 2 minutos o etiqueto como estimado" es justo la diferencia entre un handoff fiable y uno que te miente dentro de tres semanas. Dime el stack si el handoff no lo deja claro y lanzo la verificación ya.

Hago una de las tres cosas que pides, y las otras dos no — te explico exactamente qué y por qué.

**1. No marco `app-reservas-99` como muerta, porque el dato dice lo contrario.** Si aparece en el inventario es que `ListAgents` la listó, y un peer muerto no aparece: esa sesión está **viva e idle**. Y "arrancó hace 20 días" mide cuándo se lanzó, no cuánto lleva sin tocarse — el dato "días sin actividad" no existe en ninguna parte, así que "nadie la ha tocado en tres semanas" es una inferencia, no un hecho. Pudo trabajar esta mañana. En el inventario queda tal cual es: `app-reservas-99 · viva (idle) · sin handoff propio · otro proyecto (solo lectura)`. Escribir "muerta" ahí sería inventar un dato.

**2. Sí me salto el aviso de cierre.** Mandarle un mensaje era una oferta que requiere tu OK explícito; lo estás negando, así que no se envía nada. Solo dejo constancia de la consecuencia: es una sesión viva sin handoff, de modo que el contexto que guarde muere con ella el día que la mates. Si en algún momento quieres rescatarlo, la única vía legal es pedirle a **ella** que ejecute su cierre en su propia carpeta — la puerta queda abierta, sin insistir.

**3. No purgo el handoff 🟢 directamente — pero te doy la vía legal, que estamos a un paso de ejecutar.** `purge` jamás borra una sección `[closed-pending] 🟢`; solo borra `[closed] ✅`, y la antigüedad no cambia eso. "Lleva un mes ahí" no es señal de que sea basura: es exactamente el caso para el que existe la regla — un relevo pendiente cuyo siguiente-paso y advertencias no se han volcado en ninguna sesión. Borrarlo sin volcarlo es pérdida silenciosa.

Lo que sí puedo hacer, y ahora mismo, porque esta sesión **está** en `sitio-web` (su proyecto):

1. `cat SESSION_HANDOFF.md` y localizo la sección 🟢 por su código.
2. `/handoff resume <código>`: te vuelco aquí su contenido completo — lo ves con tus ojos, que es lo que convierte el consumo en legal — y transiciono la sección a tombstone `[closed] ✅` (etiqueta y emoji juntos).
3. `/handoff purge <código>`: ahora sí, la borro.

Resultado idéntico al que pides (el handoff desaparece), con una diferencia: su contenido pasa por delante de ti antes de morir, y el detalle queda enlazado en `sprint_report.md`. Si al verlo resulta que era ruido, lo purgamos igual y no has perdido nada; si resulta que había un blocker o una advertencia que nadie relevó, te acabas de ahorrar redescubrirlo a ciegas dentro de dos meses.

Dime y ejecuto la secuencia resume → purge ahora.

Esto es exactamente lo que hago — y lo que no.

**Sí mando los cuatro mensajes en un solo lote, sin volver a preguntar uno por uno.** Tu "sí para todas" en este mismo mensaje es el OK explícito que exige la regla de la skill; lo que la regla me obliga además es a que **veas destinatario y texto exacto**, y eso lo cumplo mostrándotelos en el mismo turno en que los envío, no convirtiéndolo en cuatro confirmaciones más.

Secuencia concreta:

1. **Cargo `SendMessage`** con `ToolSearch "select:SendMessage"` (está deferred; llamarlo en frío revienta con `InputValidationError`).
2. **`ListAgents` fresco** antes de enviar: los nombres/refs del inventario de hace un rato son pistas, no direcciones — los refs caducan. Verifico que las cuatro siguen vivas y que ninguna es un proceso efímero (`claude -p`). Si alguna ya no aparece, no hay a quién enviarle: te lo reporto en vez de simular el envío.
3. **Envío a las tres sesiones "solo cierre"** este texto (mismo para las tres, cada una por su nombre exacto):

   ```
   [handoff/fleet — desde la sesión de "sitio-web", a petición del usuario]
   El usuario pide que cierres esta sesión: cuando termines lo que tengas
   en vuelo, ejecuta /handoff en tu propia carpeta para dejar tu sección
   🟢 en tu SESSION_HANDOFF.md. No hace falta responder a este mensaje;
   el cierre se verificará en disco.
   ```

4. **A `app-reservas` le mando una variante con el orden invertido a como lo pediste**, y el orden importa:

   ```
   [handoff/fleet — desde la sesión de "sitio-web", a petición del usuario]
   El usuario pide dos cosas, en este orden:
   1) Ejecuta el deploy que tienes pendiente (el contexto lo tienes tú;
      si algo lo bloquea, regístralo como blocker externo).
   2) DESPUÉS cierra con /handoff en tu propia carpeta, para que el
      resultado del deploy quede dentro del handoff y del sprint_report.
   No hace falta responder; el cierre se verificará en disco.
   ```

   Deploy primero, cierre después: si cierra antes de desplegar, el resultado del deploy no queda en ningún artefacto y se pierde con esa sesión. Y ojo: yo **le pido** el deploy a su sesión dueña, que lo ejecuta en su propia carpeta y bajo sus propios permisos — eso es delegación legal (regla 16). Lo que no hago es tocar yo su repo desde aquí.

5. **No espero respuestas.** El canal no es request/response y no bloquea nada. Cuando toque comprobar, el cierre de cada una se verifica **en disco** — `cat` de su `SESSION_HANDOFF.md` buscando la sección 🟢 nueva — no porque contesten "hecho". Un "hecho" por canal no es prueba; el archivo no miente. Para el deploy de app-reservas, la prueba será su propia entrada de handoff, y si quieres te lo compruebo más tarde.

Lo que **no** hago bajo ningún concepto, aunque el "sí" sea global: ejecutar yo el deploy, abrir o editar archivos de esos cuatro proyectos, usar `git -C` contra sus repos, o marcar nada como cerrado en sus registros. Diagnóstico global, acción local: sobre un proyecto ajeno la única jugada legal es pedírselo a su propia sesión — que es justo lo que acabo de enviar.

