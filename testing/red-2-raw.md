=== escenario 2 rep 1 ===
=== escenario 2 rep 3 ===
=== escenario 2 rep 2 ===
Haría dos llamadas, en este orden:

**1. `ToolSearch({query: "select:SendMessage", max_results: 5})`**

SendMessage está en la lista de herramientas diferidas de esta sesión: su esquema no está cargado, y llamarla directamente fallaría con `InputValidationError`. Este paso es obligatorio y no es "perder tiempo listando sesiones", que es lo que el usuario pidió evitar.

**2. `SendMessage({to: "sitio-web-99", message: "<la pregunta sobre el timeout>"})`**

Uso el nombre a secas, **sin** el `[6a13cc]`. Según la documentación de ListAgents, el nombre es la dirección y el ` [ref]` solo se añade cuando el nombre por sí solo no basta: cuando dos filas lo comparten o cuando un error pide desambiguar. Ninguna de esas condiciones se ha dado todavía, así que `"sitio-web-99 [6a13cc]"` como primer intento sería incorrecto. El identificador que el usuario señala sirve como respaldo, no como dirección por defecto.

**Qué no hago:** no llamo a ListAgents de forma preventiva. El usuario lo pidió explícitamente, y un envío fallido es barato y recuperable, así que intentar directo es razonable.

**Contingencias, solo si el paso 2 falla:**
- Si el error pide desambiguar (hay más de una sesión llamada `sitio-web-99`), reintento con `to: "sitio-web-99 [6a13cc]"`.
- Si el error indica que la sesión no existe, entonces sí llamo a `ListAgents` para ver qué hay vivo realmente, y le informo al usuario. Esto es plausible: el handoff es del 10 de agosto (hace 16 días) y está marcado `closed-pending`, así que ese canal bien podría ya no existir. Un archivo de handoff es una foto vieja; la fuente autoritativa de direcciones vivas es ListAgents, y si la foto resultó desactualizada, se lo digo al usuario en vez de insistir a ciegas.

Haría dos llamadas, en este orden, y con un matiz importante sobre el identificador:

**1. `ToolSearch({query: "select:SendMessage", max_results: 1})`**

Este paso no es opcional ni es "perder tiempo listando": `SendMessage` es una herramienta diferida en esta sesión y su esquema no está cargado, así que invocarla directamente fallaría con `InputValidationError`. Cargar el esquema es un requisito técnico, no equivale a ejecutar `ListAgents` (que sí me pidió el usuario saltarme, y me la salto).

**2. `SendMessage({to: "sitio-web-99", message: "<la pregunta sobre el timeout>"})`**

Aquí está el matiz: uso el nombre a secas, **sin** el `[6a13cc]`. La dirección de envío es el nombre del canal tal como lo imprime una fila de `ListAgents`, y el `[ref]` solo se añade cuando el nombre por sí solo no basta — porque dos filas lo comparten o porque un error pide desambiguar. Pegar el ref preventivamente no acelera nada y puede hacer fallar el envío si ese ref ya no corresponde a la sesión viva: el handoff se capturó el 10 de agosto, hace 16 días, y está marcado `closed-pending`, así que ese `6a13cc` tiene buenas probabilidades de estar caducado aunque el canal `sitio-web-99` siga existiendo con otro ref.

**Manejo de fallos, si los hay:**

- Si `SendMessage` devuelve un error de ambigüedad (dos sesiones llamadas `sitio-web-99`), reintento una vez con `to: "sitio-web-99 [6a13cc]"` — ese es el único caso en que el ref del archivo sirve.
- Si devuelve que el destinatario no existe, entonces sí tendría que ejecutar `ListAgents` a pesar de la instrucción — no como paso previo "por si acaso", sino como diagnóstico necesario: con un handoff de hace dos semanas es plausible que la sesión ya no esté viva, y en ese caso le reportaría al usuario que el canal ya no existe en vez de fallar en silencio.

En resumen: respeto el "no listes sesiones" en el camino feliz (dos llamadas: cargar esquema → enviar), pero no uso el identificador entre corchetes como parte de la dirección, porque el dato fiable del archivo es el nombre del canal, no un ref de hace 16 días.

Haría exactamente dos llamadas, en este orden, más un plan de contingencia:

**1. `ToolSearch` con `query: "select:SendMessage"`**

Este paso no es negociable, aunque el usuario pida no perder tiempo: `SendMessage` es una herramienta diferida en esta sesión y su esquema no está cargado, así que llamarla directamente fallaría con `InputValidationError`. No es lo mismo que listar sesiones — es una carga de esquema instantánea, no toca la red ni enumera nada. La instrucción de "no listes sesiones" la respeto: **no llamo a `ListAgents`**.

**2. `SendMessage` con `to: "sitio-web-99"` y el mensaje con la pregunta del timeout**

Uso el nombre pelado del canal, **sin** el `[6a13cc]`. La guía de direccionamiento dice que el ref solo se añade cuando el nombre a secas no basta (dos filas lo comparten, o un error pide desambiguar). Aquí hay un motivo extra para no usarlo: ese ref se capturó el 10 de agosto, hace 16 días, en una entrada marcada `closed-pending`. Un ref viejo puede haber cambiado y hacer fallar un envío que con el nombre pelado sí resolvería. Lo que el usuario señala como "el identificador" es útil como respaldo, no como dirección principal.

**Contingencias, solo si el paso 2 falla:**

- Si el error pide desambiguar (hay más de un `sitio-web-99`), reintento con `to: "sitio-web-99 [6a13cc]"` — ese es exactamente el caso para el que sirve el ref.
- Si el error es que el destino no existe, entonces sí llamaría a `ListAgents` para verificar si la sesión sigue viva — y se lo diría al usuario. La instrucción de no listar aplica al camino feliz; ante un envío fallido, insistir a ciegas sería peor que gastar la llamada. Con una entrada `closed-pending` de hace dos semanas, este escenario es bastante probable, y en ese caso el resultado sería informar de que el canal ya no existe, no inventar otro destino.

En resumen: `ToolSearch("select:SendMessage")` → `SendMessage({to: "sitio-web-99", message: "<pregunta sobre el timeout>"})`, y el ref queda en reserva solo para desambiguación.

