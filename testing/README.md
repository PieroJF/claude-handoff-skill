# Evidencia TDD — canal cross-session (2026-08-26)

Instrumento: `claude -p --safe-mode --strict-mcp-config --disallowed-tools ... ` con prompt por
stdin y cwd de nombre neutro. `skillOverrides` **no aísla** en 2.1.246 — ver el archivo CONTAMINADO.
Brazo GREEN: mismo aislamiento + `--append-system-prompt-file SKILL.md`, para que el único delta
entre brazos sea el texto de la skill.

| Archivo | Qué mide | Resultado |
|---|---|---|
| `instrument-CONTAMINADO-skillOverrides.txt` | instrumento descartado | describió los 3 modos y el cuerpo de SKILL.md |
| `verify-instrument.txt` | instrumento válido | 3/3 "NO LA CONOZCO" |
| `red-1-raw.md` | RED cross-proyecto | **FALLA 3/3** — editan el proyecto ajeno |
| `red-2-raw.md` | RED ref grabado | pasa 3/3 → regla degradada a hecho informativo |
| `red-3b-raw.md` | control del contrato de respuesta | pasa 5/5 → contrato **cancelado** |
| `red-4-triggers.md` | disparo de la description nueva | 8/8 correcto (6 SÍ, 2 NO) |
| `green-esc1.md` | GREEN cross-proyecto | **3/3 cumplen** — cierran hasta el loophole de `git -C` |
| `refactor-probes.md` | 3 probes adversariales | 3/3 resistidos; 1 hueco menor detectado y cerrado |

El primer control (`red-3-control`, descartado) tenía un defecto: el prompt decía "tu contexto ha
sido compactado", dándole al modelo la respuesta buscada. `red-3b` lo corrige dando notas parciales
que no contienen la respuesta al dato preguntado.
