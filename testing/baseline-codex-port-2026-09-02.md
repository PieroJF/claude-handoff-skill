# Handoff registry RED baseline — Codex port (2026-09-02)

## Exact command

```powershell
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

Ran 9 tests in 0.013s

FAILED (failures=9)
```

The missing module is guarded deliberately, so each contract fails as an assertion instead of
producing a collection/import error. The run had nine failures, zero errors, and zero skips.
