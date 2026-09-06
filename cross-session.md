# Cross-session compatibility reference

The current contract is split by responsibility:

- [Shared protocol](references/shared-protocol.md): disk state, project binding,
  migration, close/resume/purge, authorization, and failure separation.
- [Codex runtime](references/codex-runtime.md): app tasks, task messaging, and
  collaboration subagents as separate scopes.
- [Claude Code runtime](references/claude-runtime.md): verified CLI inventory and
  optional messaging inside enabled teams.

Read the shared protocol and the adapter for the current runtime. Historical
`DESIGN-cross-session.md`, `PLAN-cross-session.md`, and old `testing/` evidence
record past observations; they do not define today's available tools or override
the current protocol. A disk handoff remains usable when its live channel is
unavailable.
