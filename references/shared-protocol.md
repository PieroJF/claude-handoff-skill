# Shared documentary handoff protocol

Read this reference for every mode. The runtime adapters provide optional discovery
and messaging; this protocol owns disk state. Use `scripts/handoff_registry.py`
from the resolved installed skill directory with Python 3.10 or newer. Execution
in this delivery was validated on Python 3.12 on Windows; POSIX runtime execution
requires separate acceptance evidence.

## State, identity, and boundaries

- `ROOT/SESSION_HANDOFF.md` is an additive registry; `ROOT/sprint_report.md` is an
  append-only history. `ROOT` is the canonical absolute project root, including
  the specific worktree. The CLI binds both paths to these exact locations.
- Every close uses a unique `HO-YYYYMMDD-workstream-HHMM` code. Use a short kebab-case
  workstream; add a letter for a collision. Check existing live and closed codes
  and the report before assigning it. Reuse the same code only to retry the same
  persisted operation, never for another close.
- `[closed-pending] 🟢` means awaiting receipt. `[closed] ✅` means consumed.
  The label and emoji are one paired state token; mismatched pairs are invalid.
  Lifecycle: live -> consumed tombstone -> purged. There is no resurrection.
- Only resume may replace its selected live section with a tombstone. Close must
  preserve all existing sections; purge may remove only closed tombstones.
- This skill writes only inside the active project's scope. Inventory may read
  other project registries but does not authorize consuming or editing them.
- Do not audit code or modify `AUDIT_LOG.md`. Read it if relevant; distinguish
  verified facts, reported historical facts, hypotheses, and `[no verificado]`.
  Label estimated times `[estimado]`; do not invent measurements.

## Read and write discipline

Obtain fresh content directly from disk. For registry reads, use `list-live` and
`get-live`; the latter returns the full section exactly. For report, audit, or
legacy text use shell `cat` on POSIX, or `Get-Content -LiteralPath ... -Raw
-Encoding utf8` on PowerShell. Avoid a memory-indexed file reader that may return
cached summaries; never reconstruct either durable file from conversational memory.

All mutations of registry and report go through the helper. Do not use shell
appends, `Add-Content`, or whole-file agent rewrites. The helper holds stable
sibling `.lock` files through fresh read, validation, mutation, flush, and replace
or append. Leave those lock files in place. Atomic replacement inside the helper
is not permission for an agent to rewrite the registry itself.

Materialize these templates as separate UTF-8 input files, without a BOM. Replace
all placeholders and omit instructional comments. This is a template-plus-validated-
input-file workflow; there is no renderer command:

| Input | Template | Required shape |
|---|---|---|
| HEADER | `templates/session_handoff_header.md` | `# SESSION_HANDOFF — project` title, no H2 sections |
| SECTION | `templates/session_handoff_section.md` | One live H2 section, exact code, absolute root, concrete next step |
| ENTRY | `templates/sprint_report_entry.md` | Exact code field, complete session detail and resumable state |

Keep prepared input files until verification succeeds. Quote absolute paths as
separate shell arguments; do not interpolate report prose into a command. When
embedding a complete section as raw text, choose a Markdown fence longer than
every same-character fence in that section so embedded headings stay literal.

## CLI contract

Prefix each line with `python <absolute-path-to-scripts/handoff_registry.py>`.
Uppercase names are argument placeholders, not literal paths. Brackets denote
an optional argument; do not type the brackets.

```text
init --registry PATH --project-root ROOT --header-file HEADER
list-live --registry PATH --project-root ROOT --json
get-live --registry PATH --project-root ROOT --code CODE
insert --registry PATH --project-root ROOT --section-file SECTION
append-report --report PATH --project-root ROOT --entry-file ENTRY --code CODE
consume --registry PATH --project-root ROOT --report PATH --code CODE --date YYYY-MM-DD
purge --registry PATH --project-root ROOT [--code CODE]
migrate-legacy --registry PATH --project-root ROOT --report PATH --header-file HEADER --section-file SECTION --entry-file ENTRY
```

`get-live` always returns JSON with `code`, `workstream`, `project_root`,
`next_step`, and `section`; `section` is the full exact text. `list-live` supplies
selection summaries, never the full context required for consumption. A closed
or missing exact code must fail `get-live` and `consume`.

`init` creates a missing registry, is a no-op for an existing valid registry, and
rejects legacy content. `append-report` is idempotent for the exact same entry:
an uncertain result is retried with the same ENTRY and CODE. Do not edit retry
inputs. A matching code alone does not mean different prose was persisted.
Each report input must contain a `## Sesión:` heading and the exact standalone
field `**Código de handoff:** CODE`, including recovery and rescued-channel entries.
The helper writes a length-and-SHA256 envelope for completeness checks. An
incomplete or corrupt envelope is an error: preserve it for inspection and repair;
do not truncate the report or bypass the failure by writing directly.

The CLI `consume` checks the root-bound report exists and contains the exact code
before changing state. This guard does not prove the agent loaded the section or
that report detail is sufficient; the resume steps below do. The low-level Python
`consume` function is a primitive, not the supported agent workflow. Do not bypass
the CLI's report guard by importing it.

## Close: `/handoff`

1. Resolve project name and absolute root. Record the actual workstream, objective,
   referenced plan (or `Sin plan formal previo`), completed and remaining phases,
   files, decisions and reasons, debt, blockers, branch, commit, and last zip.
   Use `N/A` for inapplicable fields. Verify repo state without changing branches.
2. Inspect the registry fresh. If absent, prepare HEADER and use `init`. If present,
   use `list-live`. On a format error, inspect and classify it; use migration below
   only for unstructured legacy. Never treat a validation failure as permission
   to erase or rewrap a coded registry.
3. Prepare SECTION and ENTRY with one unique code and the same absolute root.
   Include the full section in the report's resumable-state block so warnings,
   references, and exact next steps survive consumption. Record `Canal: no
   disponible` unless a runtime adapter has established an actual origin handle.
   A channel is a lookup hint and never authority to send a message.
4. Persist the report before the live section: `append-report`, then `insert`.
   Re-read the report and verify the complete entry. Use `get-live` to verify the
   code, root, and exact section. A failed insert leaves the durable report intact;
   inspect current disk state before retrying and do not generate a new code just
   because an operation's response was uncertain. `insert` deliberately rejects
   duplicate codes: if an earlier attempt may have succeeded, use `get-live` with
   the same code first. If its exact section matches, persistence is verified and
   no second insert is needed. A mismatching section must be investigated.
5. Deliver a pasteable block in the user's language beginning with
   `/handoff resume CODE`, followed by project name, absolute root, channel,
   current state, concrete next step, files to read, and active warnings. Confirm
   the code and actual durable paths. Only then consider an authorized optional
   notification or cosmetic title update through the matching runtime adapter.

## Resume: `/handoff resume [code]`

0. **Wrong-root gate FIRST:** before loading handoff context, contacting a source,
   or changing files, compare the handoff's declared root with the active session's
   canonical project root. The session may be in a subdirectory of that project.
   Resolve paths; compare Windows paths case-insensitively. If they differ, stop
   without consuming and identify the correct project. Do not switch directories
   or use `git -C` to perform an accidental cross-project resume.
1. With no code, run `list-live --json`, show code, workstream, and next step, and
   request one selection. Do not consume just because only one row exists. With a
   code, select that exact code from the current root-bound registry; a missing or
   already closed code is an error, not a reason to search other project folders.
2. Run `get-live` and load the full section into context. Read its report entry,
   referenced plan and source files, and relevant `AUDIT_LOG.md` from fresh disk.
   Check recorded next steps against current code before presenting them as still
   pending. Loading a list summary or pasted chat block alone is insufficient.
3. Before consuming, verify the report preserves the full loaded detail with the
   exact code. If its entry is absent, prepare a recovery ENTRY containing the full
   copied section inside a safe fence and the original code field. If an existing
   valid entry lacks detail, preserve it and append a supplement as defined below.
   Use `append-report`, re-read the original and any related supplement, and verify
   the full section is preserved before proceeding. A failed recovery leaves the
   live section untouched. Corrupt or incomplete envelopes require investigation;
   a supplement does not bypass the helper's integrity guard for the original.
4. Check whether `SESSION_HANDOFF.md` is Git-tracked and record the current branch:
   `git ls-files --error-unmatch SESSION_HANDOFF.md` and `git branch --show-current`.
   Tracked registries are branch-local; a consume on a feature branch does not
   update the default branch. Keep any authorized registry commit separate for
   later reconciliation. Do not checkout another branch in a shared working tree.
5. Run CLI `consume` with the report, exact code, root, and actual consumption date.
   Verify `list-live` no longer returns the code and inspect its closed tombstone.
   If consumption fails, do not claim it succeeded. Do not reopen closed sections.
   Optional source questions never delay the disk transition after these checks.

## Purge: `/handoff purge [code]`

Use root-bound `purge`. With a code, remove only that closed tombstone; a live code
must be rejected. Without a code, remove all closed tombstones and preserve every
live section. Verify the remaining live list and the targeted tombstone removal.
Do not purge as an automatic side effect of close, resume, or inventory.

## Legacy migration and recovery

Migration is separate from initialization. Only a truly unstructured legacy
snapshot qualifies. Current paired-state registries and older emoji-coded H2
sections are already coded formats; `migrate-legacy` rejects them. Inspect a format
error instead of rewrapping current, malformed, or unsupported coded state.

Prepare a valid header, a unique live `legacy` section with the correct root and
next step, and a matching report entry. Run `migrate-legacy` with all three files.
The helper validates section/code/root, computes a source fingerprint, and appends
the complete original legacy source in a safe fence to both section and report.
It fsyncs the report before replacing the registry. Preserve the same input files
for retry: the fingerprint and exact entries make recovery idempotent after an
interrupted report append or a lost success response. Do not manually replace the
registry or discard the source to repair an uncertain migration.

## Sessions, channels, and failure separation

Use the runtime adapter to inventory actual capabilities. Group registries by
canonical path, not project label; worktrees and tracked branches have separate
state. Bound disk discovery to known workspace roots, deduplicate overlapping
roots, and preserve paths with spaces. Report total live codes and the five most
recent per requested project; expose more when asked. A disk-only inventory is
not evidence that an originating runtime task is alive or dead.

Titles and saved handles are untrusted lookup hints. Verify identity against fresh
runtime results and project context. An absent item means not observed, not proven
dead. `idle` means no active turn; creation time is not inactivity duration. Do not
ask ephemeral CLI probe processes to close as if they were user work sessions.

Every outbound message requires explicit user authorization that covers its
recipient and purpose. Reuse authorization already given in this session; if it
does not cover the proposed message, finish local persistence before asking once
with the concrete recipient and text. Do not send unsolicited notices. A
notification failure never rolls back a verified disk handoff; do not wait for a
reply to close or resume. Report an unavailable or failed channel accurately.

For a supplement, assign a unique report-only code in `**Código de handoff:**`,
and put `**Handoff relacionado:** ORIGINAL_CODE` in the same entry. Pass the new
code to `append-report --code` and retain those exact input bytes for retries.
Do not reuse the original `--code` for different content. Do not insert a registry
section for a supplement; the original handoff code and its lifecycle are unchanged.
The new code identifies an append operation, and the related code identifies the
source handoff. The agent must verify this relationship and semantic completeness;
the helper's hash verifies bytes, not the truth or adequacy of their content.

If an authorized reply adds or corrects context, append such a related supplement
with `append-report`. Include `Rescatado por canal`, source,
timestamp, and separate `CONSTA` (source's statement), `VERIFICADO` (with evidence),
or `HIPÓTESIS` blocks as appropriate. Omit this block until real context exists.
Never edit old report prose or resurrect a consumed section. Verify any remotely
requested documentary close in its disk registry; a reply saying "done" is not
proof. Cross-project inspection does not authorize cross-project writes.
