# Dual-runtime acceptance — 2026-09-06

## Verified installation and helper

- Independent review approved implementation commit `801f73c` with no remaining
  actionable findings. Three reported findings were reproduced and fixed: Windows
  legacy stdout encoding, invalid report headings being appended before validation,
  and legacy close selection relying on an empty live list. An additional literal
  template preservation case was reproduced and fixed before approval.
- Canonical and installed Claude-junction suites each passed 58 tests on Windows
  with Python 3.12.10, exit 0. The official skill validator passed on both paths
  using `-B -X utf8`. Git diff validation passed.
- The physical Claude directory was preserved outside the repository, then replaced
  by a junction to the canonical skill. Every tracked file matched by SHA-256
  through both installation paths. Original recovery content remained unchanged.
- A separate installed-helper smoke executed seven real subprocess commands in a
  temporary project: init, append-report, insert, get-live, consume, list-live,
  purge. All exited 0. The decoded full section matched input exactly, consumption
  created its tombstone, purge removed only that tombstone, and the report hash
  remained unchanged after purge. An initial smoke assertion compared LF source
  text with Windows CRLF file bytes; the fixture comparison was corrected to use
  actual input bytes. This was a test-harness mismatch, not a helper change.

## Fresh runtime behavior

Both probes invoked the installed skill in a new CLI process against an isolated
wrong-project fixture. They were read-only capability/boundary checks, not claims
of live app API execution or model-driven registry mutation.

| Runtime | CLI | Exit | Observed behavior |
|---|---|---|---|
| Codex | 0.153.4 | 0 | Read canonical SKILL, shared protocol and Codex adapter; refused wrong-root resume; distinguished app tasks from current-tree subagents; reported app-task APIs unavailable instead of inventing calls |
| Claude Code | 2.1.259 | 0 | Expanded installed `/handoff`, read shared protocol and Claude adapter through the junction; refused wrong-root resume; distinguished CLI inventory from conditional Agent Teams messaging |

Both correctly explained that `list-live` returns selection summaries and `get-live`
returns the exact full section. Neither consumed, migrated, changed project, or sent
messages. Codex took 50.23 seconds, Claude 28.66 seconds; each process had a 180-second
limit. CLI help separately verified Claude `agents --json --cwd` support.

Commands used: Codex `exec --ephemeral --sandbox read-only --skip-git-repo-check --json`
with explicit fixture `-C`, output file `-o`, and prompt on stdin. Claude `-p
--strict-mcp-config --tools Skill,Read --allowedTools Skill,Read --permission-mode
dontAsk --permission-prompts none --no-session-persistence --no-chrome --output-format
stream-json --verbose`, with the fixture as cwd and prompt on stdin.

Exact local artifact paths, per-command output, backup locations, and installation
manifests are retained in the private controller ledger and acceptance report.
POSIX portability is implemented but was not execution-tested; no usable WSL
environment was established. Live notification delivery was not exercised.
