---
name: handoff
description: Use when the user invokes /handoff, /handoff resume, /handoff purge, or /handoff sessions, or explicitly asks to close a session, preserve progress for handover, resume a workstream, clean consumed handoffs, or inventory open sessions. Includes “cierra la sesión”, “guarda el progreso”, “retoma la sesión” and “sesiones sin cerrar”. Do not trigger for code audits or ambiguous requests to save or finish a single item.
---

# Handoff

Preserve project work across sessions using an additive `SESSION_HANDOFF.md`
registry and append-only `sprint_report.md`. Produce a pasteable handover with its
unique code and absolute project root. This skill manages documentary state; it
does not audit code, deploy, change checkouts, or create tasks.

## Required routing

Read [shared-protocol.md](references/shared-protocol.md) for every mode. All disk
mutations use `scripts/handoff_registry.py` with prepared UTF-8 input files from
`templates/`. Never replace the registry or append the report directly.

Determine the runtime from the actual environment and callable tool schemas:

- **Codex:** read [codex-runtime.md](references/codex-runtime.md). Codex tasks are
  app-level conversations; collaboration subagents belong to the current task
  tree. Their identifiers and operations are distinct.
- **Claude Code:** read [claude-runtime.md](references/claude-runtime.md). Claude teams
  permit only capabilities actually exposed for known teammates.
- **Unrecognized or unavailable live capabilities:** use the shared disk protocol;
  describe the missing optional capability without inventing a tool.

Read only the adapter for the active runtime. A session inventory is read-only;
message delivery and session identity are never prerequisites for persistence.

## Mode selection

| Request | Mode and mandatory action |
|---|---|
| `/handoff`, close this session, “cierra la sesión” | Close: persist report, insert live section, verify both, return pasteable handover |
| `/handoff resume [code]`, resume a workstream | Resume: validate project root before loading context or making any change; select exact live code, load full detail, verify durable report, consume and verify |
| `/handoff purge [code]` | Purge: remove only consumed tombstones inside the bound project |
| `/handoff sessions`, inventory open sessions | Sessions: use the actual runtime inventory, correlate read-only disk state, label scope and unknowns |

With no resume code, list live choices and ask for one selection. A missing or
already consumed code must fail; never resurrect it. Root mismatch stops resume
before loading referenced files, contacting a source, or consuming anything.
Fresh disk detail governs handover; a saved next step still needs checking against
current project state before it is treated as pending work.

## Authorization and success

Outbound messages require explicit user authorization covering recipient and
purpose. Preserve valid authorization already given; do not add a repeated
approval checkpoint. Without it, complete and verify local persistence first,
then present the concrete message if user input is needed. A failed or unavailable
notification does not invalidate a disk handoff and must not be reported as sent.

Before claiming success, verify the exact code, project root, durable report, and
resulting registry state using the helper and fresh disk reads. Report factual
results and any failed optional capability. Templates retain required fields;
use `N/A` when inapplicable, `[no verificado]` when unknown, and `[estimado]` for
estimates. Detailed state transitions, migration, recovery, and channel rules live
in the required shared protocol.
