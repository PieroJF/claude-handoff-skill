# Claude Code runtime adapter

Use only for Claude Code. Read `shared-protocol.md` first. Verify the installed
CLI and currently exposed tool schemas; historical plugin tools are not a global
runtime contract.

## Session discovery

Check `claude agents --help` before relying on version-sensitive flags. Claude
Code 2.1.259 verified on 2026-09-06 supports `--json` and `--cwd`; its JSON listing
includes background agents and interactive sessions. This is an observation about
that installed CLI, not proof that all historical versions support the flags.

```powershell
$projectRoot = git rev-parse --show-toplevel 2>$null
if (-not $projectRoot) { $projectRoot = (Get-Location).Path }
$projectRoot = (Resolve-Path -LiteralPath $projectRoot).Path
claude agents --json --cwd $projectRoot
```

Check command exit status and read the actual JSON shape before using fields. An
explicit project path takes precedence over inference. The root must still pass
the shared protocol's binding gate. If the CLI or flags are absent, use local disk
handoff and report that live session discovery is unavailable. A disk registry
can identify pending handoffs but cannot prove the originating session is alive.

There is no global `ListAgents` tool promised by Claude Code. The CLI listing is
not a list of messageable peers. Do not infer a writable communication channel
from a session ID, process name, or title in this inventory.

## Team messaging is conditional

`SendMessage` may be used only when its actual callable schema is exposed inside
enabled Agent Teams and the recipient is a known teammate supported by that
schema. Verify the current recipient, capability, and project context. A session
listed by `claude agents` does not automatically become a teammate or resumable
subagent. Never promise arbitrary global cross-session messaging.

Require explicit user authorization for the concrete recipient and purpose, as
defined in the shared protocol. Use only arguments supported by the loaded tool
schema. If the team capability is absent, or the intended recipient is outside
its scope, finish the local disk handoff and state that live notification was
skipped. Do not install or invent messaging tools to complete a close.

Sending does not prove delivery, a reply, or a documentary close. Do not block
close or resume waiting for a response. If an authorized reply supplies useful
context later, append a uniquely identified supplement linked to the original
handoff code as required by the shared protocol. Never undo successful
disk persistence because messaging failed.

Record a channel only from verified current identity, including runtime and scope;
otherwise write `Canal: no disponible`. Re-resolve any stored hint before sending.
An unavailable handle is not proof a session died, and `idle` is not elapsed
inactivity. A cosmetic `/rename [closed] <workstream>` may be offered when useful;
the agent must not pretend a printed slash-command executed. Registry state
remains canonical regardless of the session title.
