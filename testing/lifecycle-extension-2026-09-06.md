# Lifecycle helper extension evidence

The extension preserves the Task 6 Python primitives and makes the runtime CLI enforce
the project-bound protocol. It adds `init`, `get-live`, `migrate-legacy`, idempotent report
append, and report verification before consumption. Read runtime instructions in
`references/shared-protocol.md`.

## Test-first evidence

- Initial lifecycle suite: 11 deliberate assertion failures, zero unittest errors.
  Missing APIs and an observed foreign-project purge demonstrated the required changes.
- First implementation: 36 registry tests passed (25 existing and 11 new).
- Additional negative tests exposed shortened duplicate report content and a bare report
  code incorrectly authorizing consumption: two assertion failures, then corrected.
- Integrated helper suite: `python -B -m unittest discover -s tests -p 'test*registry*.py' -q`
  ran 40 tests, all passed, exit 0 on Windows. This includes independent-process init and
  report append, existing insert concurrency, and a real subprocess CLI lifecycle.

The tests use temporary projects. They cover exact source preservation with CRLF and an
unclosed code fence, report-first migration, injected `os.replace` and `fsync` failures,
idempotent retry, incomplete or modified report envelopes, and wrong-project/closed-code
rejection. No actual project registry is used as a fixture.

## Durability and portability

Report entries written by the safe CLI carry byte length and SHA-256 integrity metadata;
unfenced code and session heading checks also support historical report entries. A torn
append fails closed: it is preserved for explicit repair, never silently truncated.
Registry replacement fsyncs the temporary file; POSIX also fsyncs the parent directory.
Windows uses stable sidecar locks with `msvcrt`, POSIX uses `flock`. Linux/WSL execution
was unavailable on this host; POSIX behavior is implemented but not execution-tested.

The existing blocking lock contract is retained. An external runtime should bound helper
execution and report a timeout; it must never delete the lock file to force access. Plain
listing and stderr escape terminal controls. Runtime adapters consume JSON output.

## Preservation

Both the original canonical directory (including Git history, dirty SKILL.md, templates,
and recovery document) and the distinct Claude installation were copied to an external
timestamped skill-backup directory before any edit. Exact local backup paths and SHA-256
proof belong in the private controller ledger. The recovery document stays locally
available and is excluded from this repository's published files.
