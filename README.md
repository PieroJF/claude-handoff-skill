# Handoff

A documentary session handoff skill for **Codex and Claude Code**. Parallel
workstreams preserve their own resumable state in one additive project registry.
The shared Python helper serializes mutations so closing one session does not
erase another session's pending handoff.

```text
[closed-pending] 🟢 live -> [closed] ✅ consumed tombstone -> purged
```

`SESSION_HANDOFF.md` holds pending handoffs by unique code and absolute project
root. `sprint_report.md` retains session history and complete resumable detail.
The chat handover block carries the exact resume command, root, next step, and
warnings. Notifications are optional and require explicit user authorization.

## Modes

| Request | Result |
|---|---|
| `/handoff` | Save report, insert live section, verify, print handover |
| `/handoff resume CODE` | Validate project root, load full section, verify report, consume exact code |
| `/handoff resume` | List live choices and request selection |
| `/handoff purge [CODE]` | Remove only consumed tombstones |
| `/handoff sessions` | Inventory available runtime sessions and read-only disk state |

Codex can also explicitly invoke the skill as `$handoff`; natural-language close,
resume, purge, and inventory requests are covered by its trigger description.
Skill invocation is not the same as a runtime's native conversation `/resume`.

## Canonical installation

Requirements: Python 3.10 or newer, a runtime with filesystem/command execution,
and the complete skill directory. No external Python packages are needed by the
helper or unit tests. Keep one Git-backed canonical copy under
`C:\Users\Piero\.agents\skills\handoff`; on this Windows host the Claude Code path
`C:\Users\Piero\.claude\skills\handoff` should be a directory junction to it.
Codex uses the canonical skill and its `agents/openai.yaml` metadata.

For a **new installation** with both target paths absent:

```powershell
$canonical = Join-Path $env:USERPROFILE '.agents\skills\handoff'
$claudePath = Join-Path $env:USERPROFILE '.claude\skills\handoff'
if (Test-Path -LiteralPath $canonical) { throw 'Canonical target already exists.' }
if (Test-Path -LiteralPath $claudePath) { throw 'Claude target already exists; back it up first.' }
git clone https://github.com/PieroJF/claude-handoff-skill.git $canonical
if ($LASTEXITCODE -ne 0) { throw 'Clone failed.' }
New-Item -ItemType Directory -Path (Split-Path -Parent $claudePath) -Force | Out-Null
New-Item -ItemType Junction -Path $claudePath -Target $canonical | Out-Null
```

For an existing installation, preserve its entire directory and any dirty Git diff
before replacing or linking it. Do not run a fresh clone over an installed copy.
On POSIX hosts, use the runtime's supported canonical skills directory and a
corresponding symlink for the Claude path. Verify discovery in fresh runtime
sessions; a junction or a passing static test alone does not prove discovery.

## Protocol and files

- [SKILL.md](SKILL.md) is the short mode and runtime router.
- [Shared protocol](references/shared-protocol.md) documents every supported CLI
  command, input format, root gate, migration, and recovery sequence.
- [Codex adapter](references/codex-runtime.md) distinguishes app tasks from
  subagents. [Claude adapter](references/claude-runtime.md) verifies CLI inventory
  and limits team messaging to exposed capabilities.
- `templates/session_handoff_header.md`, `session_handoff_section.md`, and
  `sprint_report_entry.md` are separate templates for prepared UTF-8 input files.
- `scripts/handoff_registry.py` performs all registry/report mutations. There is
  no renderer; substitute template fields before invoking the CLI.
- `tests/` covers registry safety and document contracts; `testing/` retains
  observed RED evidence and behavioral probes.

Registry/report paths bind to the declared project's `SESSION_HANDOFF.md` and
`sprint_report.md`. `init`, `migrate-legacy`, and `get-live` are separate operations.
Only true unstructured legacy snapshots may be migrated; already coded formats
must not be rewrapped. Reads and writes must preserve fresh disk state. Never use
shell appends or rewrite the registry from memory.

## Verification

```powershell
python -m unittest discover -s 'C:\Users\Piero\.agents\skills\handoff\tests' -v
python -m compileall -q 'C:\Users\Piero\.agents\skills\handoff\scripts' 'C:\Users\Piero\.agents\skills\handoff\tests'
python 'C:\Users\Piero\.agents\skills\handoff\scripts\handoff_registry.py' --help
```

For structural validation, use the installed skill creator's `quick_validate.py`
with its Python environment containing PyYAML and `python -X utf8` on Windows.
Fresh Codex and Claude acceptance
probes are separate and must exercise capability boundaries and disk-only fallback.
This skill does not audit code, change checkouts, or deploy a project.

## License

[MIT](LICENSE)
