# Dual-runtime documentation contracts

## RED observed on 2026-09-06

Before changing any production documentation, ran:

```powershell
python -m unittest discover -s 'C:/Users/Piero/.agents/skills/handoff/tests' -p 'test_runtime_contracts.py' -v
python -m unittest discover -s 'C:/Users/Piero/.agents/skills/handoff/tests' -p 'test_skill_contract.py' -v
```

Observed six assertion failures in each suite, zero collection errors. The runtime
references were absent. The old entrypoint was 7,235 whitespace-delimited words,
contained obsolete global-peer assumptions, and lacked the routing contract. The
header template and Codex metadata were absent; the report template contained an
unfilled rescued-channel block; the compatibility reference was not a pointer.

These are executable document-contract failures, not invented model transcripts.
Historical agent pressure baselines remain under `testing/`. Fresh runtime
acceptance is separate from static document validation.

## Verification scope

The contracts check runtime capability boundaries, all CLI command signatures,
root and persistence gates, short routing, separate input templates, and Codex
metadata. Registry execution and concurrency are tested by the helper suite.
Fresh runtime behavior must be checked separately before claiming installation
compatibility; a static pass alone is insufficient.

## GREEN observed on 2026-09-06

Both commands above passed: six runtime contracts and six skill contracts, with
zero failures. `claude agents --help` confirmed `--cwd` and `--json`; the latter
explicitly includes interactive and background sessions. The official validator
initially failed under the host's cp1252 default decoding; rerunning its unchanged
script with Python's `-X utf8` is the Windows-compatible invocation used here.
That rerun reported `Skill is valid!`; compilation of the two contract test files
and `git diff --check` also passed. Git emitted only existing LF/CRLF conversion
notices. No POSIX runtime compatibility claim is made from this Windows run.
