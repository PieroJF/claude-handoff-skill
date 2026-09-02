# Handoff registry RED baseline — Codex port (2026-09-02)

## Exact command

```powershell
Set-Location -LiteralPath 'C:\Users\Piero\.agents\skills\handoff'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m unittest discover -s 'C:\Users\Piero\.agents\skills\handoff\tests' -v
```

## Observed output

```text
test_append_report_preserves_existing_bytes (...) ... FAIL
test_concurrent_inserts_keep_both_sections (...) ... FAIL
test_consumes_exact_code_to_one_line_tombstone (...) ... FAIL
test_inserts_without_changing_existing_sections (...) ... FAIL
test_lists_only_live_sections (...) ... FAIL
test_purges_only_consumed_tombstones (...) ... FAIL
test_rejects_already_consumed_code (...) ... FAIL
test_rejects_duplicate_live_code (...) ... FAIL
test_rejects_wrong_project_root (...) ... FAIL

AssertionError: scripts.handoff_registry is not implemented; Task 6 must provide the shared registry API.

Ran 9 tests in 0.016s

FAILED (failures=9)
```

The explicit repository change makes the command reproducible from any caller directory. The
missing module is guarded deliberately, so each contract fails as an assertion instead of producing
a collection/import error. The run had nine failures, zero errors, and zero skips.

## Approved concurrency lock contract

`test_concurrent_inserts_keep_both_sections` uses two independently terminable OS processes and
holds the public sibling sidecar before releasing both writers together. Its lock target is exactly
`<registry filename>.lock`; therefore the canonical `SESSION_HANDOFF.md` registry uses
`SESSION_HANDOFF.md.lock`.

The sidecar is stable across `os.replace`: the registry path is replaced with each atomic snapshot,
while `SESSION_HANDOFF.md.lock` remains the same lock identity for the complete read, validation,
mutation, flush, and replacement critical section. A process-local lock or no interprocess lock
allows a writer to finish while the parent holds this sidecar and fails the contract. The workers
are joined with bounded cleanup, terminated if needed, and must report clean exit statuses and two
surviving distinct sections after release.
