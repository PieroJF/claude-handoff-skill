"""Atomic operations for the SESSION_HANDOFF registry."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import ntpath
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import posixpath
import re
import stat
import sys
import tempfile


class RegistryError(RuntimeError):
    """Raised when registry data or an operation is invalid."""


@dataclass(frozen=True)
class _Section:
    start: int
    end: int
    state: str
    code: str
    workstream: str
    project_root: str | None = None
    next_step: str | None = None


@dataclass(frozen=True)
class _MarkdownLine:
    start: int
    end: int
    text: str


_HANDOFF_HEADER = re.compile(
    r"## \[(?P<state>[^\]\r\n]+)\] (?P<symbol>\S+) "
    r"(?P<code>\S+) — (?P<details>[^\r\n]+)"
)
_TOMBSTONE_DETAILS = re.compile(
    r"(?P<workstream>.+?) · consumido (?P<consumed>\d{4}-\d{2}-\d{2}) "
    r"· detalle en sprint_report\.md"
)
_PROJECT_ROOT_LINE = re.compile(
    r"> Proyecto: (?P<project>.+?) · raíz: (?P<root>[^\r\n]+)"
)
_FENCE_OPEN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_HANDOFF_CODE = re.compile(r"(?:^|\s)HO-\S+")
_VALID_STATES = {
    ("closed-pending", "🟢"): "live",
    ("closed", "✅"): "closed",
}


def _read_utf8(path: Path, description: str) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RegistryError(f"Cannot read {description} '{path}': {error}") from error
    try:
        return raw, raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RegistryError(f"{description.capitalize()} '{path}' is not valid UTF-8.") from error


def _outside_fence_lines(text: str) -> list[_MarkdownLine]:
    lines: list[_MarkdownLine] = []
    offset = 0
    fence: str | None = None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if fence is not None:
            marker = re.escape(fence[0])
            if re.fullmatch(rf" {{0,3}}{marker}{{{len(fence)},}}[ \t]*", line):
                fence = None
        else:
            opening = _FENCE_OPEN.fullmatch(line)
            if opening is not None and not (
                opening["fence"].startswith("`") and "`" in opening["info"]
            ):
                fence = opening["fence"]
            else:
                lines.append(_MarkdownLine(offset, offset + len(raw_line), line))
        offset += len(raw_line)
    if fence is not None:
        raise RegistryError(f"Unterminated fenced code block opened with '{fence}'.")
    return lines


def _top_level_headers(text: str) -> list[_MarkdownLine]:
    return [line for line in _outside_fence_lines(text) if line.text.startswith("## ")]


def _parse_next_step(body: str, code: str) -> str:
    lines = _outside_fence_lines(body)
    headings = [line for line in lines if line.text == "### Siguiente paso concreto"]
    if len(headings) != 1:
        raise RegistryError(f"Live handoff '{code}' must have one next-step heading.")

    start = headings[0].end
    end = next(
        (line.start for line in lines if line.start >= start and line.text.startswith("### ")),
        len(body),
    )
    prefix = "- **Descripción:** "
    descriptions = [
        line.text[len(prefix) :]
        for line in lines
        if start <= line.start < end and line.text.startswith(prefix)
    ]
    if len(descriptions) != 1 or not descriptions[0].strip():
        raise RegistryError(f"Live handoff '{code}' must have one concrete next step.")
    return descriptions[0]


def _parse_sections(text: str) -> list[_Section]:
    headers = _top_level_headers(text)
    sections: list[_Section] = []
    seen_codes: set[str] = set()

    for index, header in enumerate(headers):
        line = header.text
        match = _HANDOFF_HEADER.fullmatch(line)
        if match is None:
            if line.startswith("## [") or _HANDOFF_CODE.search(line):
                raise RegistryError(f"Malformed handoff header: {line}")
            continue

        pair = (match["state"], match["symbol"])
        state = _VALID_STATES.get(pair)
        if state is None:
            raise RegistryError(
                f"Invalid state pair '[{match['state']}] {match['symbol']}' "
                f"for handoff '{match['code']}'."
            )

        code = match["code"]
        if code in seen_codes:
            raise RegistryError(f"Duplicate handoff code '{code}'.")
        seen_codes.add(code)

        details = match["details"]
        end = headers[index + 1].start if index + 1 < len(headers) else len(text)
        if state == "closed":
            tombstone = _TOMBSTONE_DETAILS.fullmatch(details)
            if tombstone is None:
                raise RegistryError(f"Malformed consumed tombstone for handoff '{code}'.")
            try:
                date.fromisoformat(tombstone["consumed"])
            except ValueError as error:
                raise RegistryError(f"Invalid consumed date for handoff '{code}'.") from error
            sections.append(
                _Section(header.start, end, state, code, tombstone["workstream"])
            )
            continue

        if " · consumido " in details or not details.strip() or details != details.strip():
            raise RegistryError(f"Malformed live header for handoff '{code}'.")
        body = text[header.end : end]
        project_lines = [
            line.text
            for line in _outside_fence_lines(body)
            if line.text.startswith("> Proyecto:")
        ]
        if len(project_lines) != 1:
            raise RegistryError(f"Live handoff '{code}' must have one project-root line.")
        project = _PROJECT_ROOT_LINE.fullmatch(project_lines[0])
        if (
            project is None
            or not project["project"].strip()
            or not project["root"].strip()
            or project["root"] != project["root"].strip()
        ):
            raise RegistryError(f"Live handoff '{code}' has an invalid project-root line.")
        _path_key(project["root"])
        sections.append(
            _Section(
                header.start,
                end,
                state,
                code,
                details,
                project["root"],
                _parse_next_step(body, code),
            )
        )
    return sections


def _path_key(path: Path | str) -> str:
    raw = str(path)
    windows_absolute = PureWindowsPath(raw).is_absolute()
    posix_absolute = PurePosixPath(raw).is_absolute()
    if not windows_absolute and not posix_absolute:
        raise RegistryError(f"Project root '{path}' must be an absolute path.")

    try:
        if windows_absolute and (os.name == "nt" or not posix_absolute):
            resolved = str(Path(path).resolve()) if os.name == "nt" else ntpath.normpath(raw)
            return f"windows:{ntpath.normcase(resolved).casefold()}"
        resolved = str(Path(path).resolve()) if os.name != "nt" else posixpath.normpath(raw)
        return f"posix:{resolved}"
    except (OSError, RuntimeError, ValueError) as error:
        raise RegistryError(f"Cannot resolve project root '{path}': {error}") from error


def _matches_root(section: _Section, project_root: Path) -> bool:
    if section.project_root is None:
        raise RegistryError(f"Live handoff '{section.code}' has no project root.")
    return _path_key(section.project_root) == _path_key(project_root)


def _sidecar_path(target: Path) -> Path:
    if not target.name:
        raise RegistryError(f"Target path '{target}' must include a filename.")
    try:
        return target.with_name(f"{target.name}.lock")
    except ValueError as error:
        raise RegistryError(f"Target path '{target}' must include a filename.") from error


def _resolve_target(path: Path | str, description: str) -> Path:
    try:
        target = Path(path).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise RegistryError(f"Cannot resolve {description} path '{path}': {error}") from error
    if not target.name:
        raise RegistryError(f"{description.capitalize()} path '{path}' must include a filename.")
    if target.exists() and not target.is_file():
        raise RegistryError(f"{description.capitalize()} path '{path}' is not a regular file.")
    return target


def _reject_multiple_links(target: Path, description: str) -> None:
    try:
        metadata = target.stat()
    except OSError as error:
        raise RegistryError(f"Cannot inspect {description} '{target}': {error}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise RegistryError(f"{description.capitalize()} '{target}' is not a regular file.")
    if metadata.st_nlink > 1:
        raise RegistryError(
            f"{description.capitalize()} '{target}' has multiple hard links; mutation is unsafe."
        )


def _same_file(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError as error:
        raise RegistryError(f"Cannot compare '{first}' and '{second}': {error}") from error


@contextmanager
def _exclusive_lock(target: Path) -> Iterator[None]:
    sidecar = _sidecar_path(target)
    try:
        handle = sidecar.open("a+b")
    except OSError as error:
        raise RegistryError(f"Cannot open lock sidecar '{sidecar}': {error}") from error

    with handle:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError as error:
            raise RegistryError(f"Cannot acquire lock '{sidecar}': {error}") from error

        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_replace(target: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        if target.exists():
            _reject_multiple_links(target, "registry")
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=target.parent) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        if os.name != "nt":
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except BaseException as error:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as cleanup_error:
                raise RegistryError(
                    f"Cannot replace '{target}', and temporary cleanup failed: {cleanup_error}"
                ) from error
        if isinstance(error, OSError):
            raise RegistryError(f"Cannot replace registry '{target}': {error}") from error
        raise


def _registry_state(registry: Path) -> tuple[bytes, str, list[_Section]]:
    raw, text = _read_utf8(registry, "registry")
    return raw, text, _parse_sections(text)


def list_live(registry: Path, project_root: Path) -> list[dict[str, str]]:
    registry = _resolve_target(registry, "registry")
    _path_key(project_root)
    with _exclusive_lock(registry):
        _, _, sections = _registry_state(registry)
        return [
            {
                "code": section.code,
                "workstream": section.workstream,
                "project_root": section.project_root,
                "next_step": section.next_step,
            }
            for section in sections
            if section.state == "live" and _matches_root(section, project_root)
        ]


def _boundary_separator(content: bytes) -> bytes:
    newline = b"\r\n" if b"\r\n" in content else b"\n"
    if content.endswith(newline * 2):
        return b""
    if content.endswith(newline):
        return newline
    return newline * 2


def insert_section(registry: Path, section_file: Path, project_root: Path) -> None:
    registry = _resolve_target(registry, "registry")
    _reject_multiple_links(registry, "registry")
    section_raw, section_text = _read_utf8(Path(section_file), "section file")
    new_sections = _parse_sections(section_text)
    section_headers = _top_level_headers(section_text)
    if (
        len(new_sections) != 1
        or len(section_headers) != 1
        or new_sections[0].state != "live"
        or section_text[: new_sections[0].start].strip()
    ):
        raise RegistryError("Section file must contain exactly one live handoff section.")
    new_section = new_sections[0]
    if not _matches_root(new_section, project_root):
        raise RegistryError(f"Handoff '{new_section.code}' belongs to a different project root.")

    with _exclusive_lock(registry):
        _reject_multiple_links(registry, "registry")
        original, _, sections = _registry_state(registry)
        if any(section.code == new_section.code for section in sections):
            raise RegistryError(f"Duplicate handoff code '{new_section.code}'.")
        _atomic_replace(registry, original + _boundary_separator(original) + section_raw)


def append_report(report: Path, entry_file: Path) -> None:
    report = _resolve_target(report, "report")
    entry_file = _resolve_target(entry_file, "report entry")
    if report.exists():
        _reject_multiple_links(report, "report")
    if _same_file(report, entry_file):
        raise RegistryError("Report and report entry must be different files.")
    try:
        entry = entry_file.read_bytes()
    except OSError as error:
        raise RegistryError(f"Cannot read report entry '{entry_file}': {error}") from error

    with _exclusive_lock(report):
        if report.exists():
            _reject_multiple_links(report, "report")
        if _same_file(report, entry_file):
            raise RegistryError("Report and report entry must be different files.")
        try:
            with report.open("ab") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell():
                    handle.write(b"\n\n---\n\n")
                handle.write(entry)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as error:
            raise RegistryError(f"Cannot append report '{report}': {error}") from error


def consume(registry: Path, code: str, project_root: Path, consumed_on: date) -> None:
    registry = _resolve_target(registry, "registry")
    _reject_multiple_links(registry, "registry")
    _path_key(project_root)
    with _exclusive_lock(registry):
        _reject_multiple_links(registry, "registry")
        _, text, sections = _registry_state(registry)
        section = next((item for item in sections if item.code == code), None)
        if section is None:
            raise RegistryError(f"Unknown handoff code '{code}'.")
        if section.state != "live":
            raise RegistryError(f"Handoff '{code}' is already consumed.")
        if not _matches_root(section, project_root):
            raise RegistryError(f"Handoff '{code}' belongs to a different project root.")
        if type(consumed_on) is not date:
            raise RegistryError("Consumed date must be a date value.")

        newline = "\r\n" if "\r\n" in text[section.start : section.end] else "\n"
        tombstone = (
            f"## [closed] ✅ {section.code} — {section.workstream} "
            f"· consumido {consumed_on.isoformat()} · detalle en sprint_report.md"
            f"{newline}{newline}"
        )
        updated = text[: section.start] + tombstone + text[section.end :]
        _atomic_replace(registry, updated.encode("utf-8"))


def purge(registry: Path, project_root: Path, code: str | None = None) -> int:
    registry = _resolve_target(registry, "registry")
    _reject_multiple_links(registry, "registry")
    _path_key(project_root)
    with _exclusive_lock(registry):
        _reject_multiple_links(registry, "registry")
        _, text, sections = _registry_state(registry)
        selected = next((section for section in sections if section.code == code), None)
        if selected is not None and selected.state != "closed":
            raise RegistryError(f"Handoff '{code}' is live and cannot be purged.")
        live_sections = [section for section in sections if section.state == "live"]
        if live_sections and not any(_matches_root(section, project_root) for section in live_sections):
            raise RegistryError("Registry has no live handoff for the supplied project root.")
        removed = [
            section
            for section in sections
            if section.state == "closed" and (code is None or section.code == code)
        ]
        if not removed:
            return 0
        updated = text
        for section in reversed(removed):
            updated = updated[: section.start] + updated[section.end :]
        _atomic_replace(registry, updated.encode("utf-8"))
        return len(removed)


def _bind_path(target: Path, project_root: Path, filename: str) -> Path:
    """Bind runtime operations to the selected project's actual canonical files."""
    _path_key(project_root)
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise RegistryError(f"Project root '{root}' is not an existing directory.")
    resolved = _resolve_target(target, filename)
    expected = root / filename
    if resolved != expected:
        raise RegistryError(f"Expected project file '{expected}', received '{resolved}'.")
    return resolved


def _validate_input(text: str, description: str) -> None:
    if not text.strip() or re.search(r"\{\{[^\n]*\}\}", text):
        raise RegistryError(f"{description} is empty or has unfilled template fields.")


def _read_header(header_file: Path) -> bytes:
    raw, text = _read_utf8(header_file, "header file")
    _validate_input(text, "Registry header")
    if not text.startswith("# SESSION_HANDOFF — ") or _top_level_headers(text):
        raise RegistryError("Header must begin '# SESSION_HANDOFF — ' and contain no sections.")
    return raw


def init_registry(registry: Path, header_file: Path, project_root: Path) -> None:
    registry = _bind_path(registry, project_root, "SESSION_HANDOFF.md")
    header = _read_header(header_file)
    with _exclusive_lock(registry):
        if registry.exists():
            _, text, _ = _registry_state(registry)
            if not text.startswith("# SESSION_HANDOFF — "):
                raise RegistryError("Existing file is not a registry; use migrate-legacy explicitly.")
            return
        _atomic_replace(registry, header)


def get_live(registry: Path, code: str, project_root: Path) -> dict[str, str]:
    registry = _bind_path(registry, project_root, "SESSION_HANDOFF.md")
    with _exclusive_lock(registry):
        _, text, sections = _registry_state(registry)
        section = _selected_live(sections, code, project_root)
        return {
            "code": section.code,
            "workstream": section.workstream,
            "project_root": section.project_root,
            "next_step": section.next_step,
            "section": text[section.start:section.end],
        }


def _selected_live(sections: list[_Section], code: str, project_root: Path) -> _Section:
    section = next((item for item in sections if item.code == code), None)
    if section is None:
        raise RegistryError(f"Unknown handoff code '{code}'.")
    if section.state != "live":
        raise RegistryError(f"Handoff '{code}' is already consumed.")
    if not _matches_root(section, project_root):
        raise RegistryError(f"Handoff '{code}' belongs to a different project root.")
    return section


_REPORT_CODE = re.compile(r"\*\*Código de handoff:\*\* (?P<code>HO-[^\s]+)[ \t]*")
_REPORT_BEGIN = re.compile(r"<!-- handoff-entry (?P<code>HO-[^\s]+) (?P<size>\d+) (?P<sha>[a-f0-9]{64}) -->")


def _report_codes(text: str) -> list[str]:
    return [match["code"] for line in _outside_fence_lines(text)
            if (match := _REPORT_CODE.fullmatch(line.text)) is not None]


def _verify_report_entry(raw: bytes, code: str) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RegistryError("Report is not valid UTF-8.") from error
    if _report_codes(text).count(code) != 1:
        raise RegistryError(f"Report must contain exactly one unfenced entry for '{code}'.")
    lines = _outside_fence_lines(text)
    code_line = next(line for line in lines if (match := _REPORT_CODE.fullmatch(line.text))
                     is not None and match["code"] == code)
    headings = [line for line in lines if line.text.startswith("## ")]
    heading = next((line for line in reversed(headings) if line.start < code_line.start), None)
    if heading is None or not heading.text.startswith("## Sesión:"):
        raise RegistryError(f"Report code '{code}' has no session entry heading.")
    end = next((line.start for line in headings if line.start > code_line.start), len(text))
    if not text[code_line.end:end].strip():
        raise RegistryError(f"Report entry '{code}' has no detail.")
    # New entries carry a length and digest so a torn append never authorizes consume.
    for line in _outside_fence_lines(text):
        match = _REPORT_BEGIN.fullmatch(line.text)
        if match is None or match["code"] != code:
            continue
        start = len(text[:line.end].encode("utf-8"))
        size = int(match["size"])
        payload = raw[start:start + size]
        closing = f"\n<!-- /handoff-entry {code} -->\n".encode("utf-8")
        if (len(payload) != size or hashlib.sha256(payload).hexdigest() != match["sha"]
                or not raw[start + size:].startswith(closing)):
            raise RegistryError(f"Incomplete or changed report entry for '{code}'; preserve and repair it before retrying.")
        return payload
    return text[heading.start:end].rstrip("\r\n- ").encode("utf-8")


def _validated_entry(entry: bytes, code: str) -> None:
    try:
        text = entry.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RegistryError("Report entry is not valid UTF-8.") from error
    _validate_input(text, "Report entry")
    if _report_codes(text) != [code] or not _top_level_headers(text):
        raise RegistryError("Entry must have a session heading and exactly one matching handoff code.")
    _verify_report_entry(entry, code)


def _append_once_locked(report: Path, entry: bytes, code: str) -> None:
    _validated_entry(entry, code)
    original = b""
    if report.exists():
        _reject_multiple_links(report, "report")
        original, text = _read_utf8(report, "report")
        codes = _report_codes(text)
        if code in codes:
            existing = _verify_report_entry(original, code)
            if entry.rstrip() != existing.rstrip():
                raise RegistryError(f"Conflicting report content already exists for '{code}'.")
            # A previous attempt may have failed during fsync; retry must make it durable.
            with report.open("ab") as handle:
                handle.flush()
                os.fsync(handle.fileno())
            return
    envelope = (
        f"<!-- handoff-entry {code} {len(entry)} {hashlib.sha256(entry).hexdigest()} -->\n".encode("utf-8")
        + entry + f"\n<!-- /handoff-entry {code} -->\n".encode("utf-8")
    )
    try:
        with report.open("ab") as handle:
            if original:
                handle.write(b"\n\n---\n\n")
            handle.write(envelope)
            handle.flush()
            os.fsync(handle.fileno())
        persisted, _ = _read_utf8(report, "report")
        _verify_report_entry(persisted, code)
    except OSError as error:
        raise RegistryError(f"Cannot persist report '{report}': {error}") from error


def append_report_once(report: Path, entry_file: Path, code: str) -> None:
    report = _resolve_target(report, "report")
    entry_file = _resolve_target(entry_file, "report entry")
    if _same_file(report, entry_file):
        raise RegistryError("Report and report entry must be different files.")
    entry, _ = _read_utf8(entry_file, "report entry")
    with _exclusive_lock(report):
        _append_once_locked(report, entry, code)


def consume_with_report(registry: Path, report: Path, code: str, project_root: Path, consumed_on: date) -> None:
    registry = _bind_path(registry, project_root, "SESSION_HANDOFF.md")
    report = _bind_path(report, project_root, "sprint_report.md")
    if type(consumed_on) is not date:
        raise RegistryError("Consumed date must be a date value.")
    # Always registry then report; migration uses the same order to avoid deadlocks.
    with _exclusive_lock(registry), _exclusive_lock(report):
        _, text, sections = _registry_state(registry)
        section = _selected_live(sections, code, project_root)
        raw, _ = _read_utf8(report, "report")
        _verify_report_entry(raw, code)
        _reject_multiple_links(report, "report")
        try:
            with report.open("ab") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as error:
            raise RegistryError(f"Cannot verify report durability: {error}") from error
        newline = "\r\n" if "\r\n" in text[section.start:section.end] else "\n"
        tombstone = (f"## [closed] ✅ {code} — {section.workstream} · consumido "
                     f"{consumed_on.isoformat()} · detalle en sprint_report.md{newline}{newline}")
        _atomic_replace(registry, (text[:section.start] + tombstone + text[section.end:]).encode("utf-8"))


def _legacy_block(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    longest = max((len(match[0]) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    digest = hashlib.sha256(raw).hexdigest()
    return (f"\n\n<!-- handoff-legacy-sha256:{digest} -->\n"
            f"### Snapshot legacy preservado\n\n{fence}text\n".encode("utf-8")
            + raw + f"\n{fence}\n".encode("utf-8"))


def migrate_legacy(registry: Path, report: Path, header_file: Path, section_file: Path,
                   entry_file: Path, project_root: Path) -> None:
    registry = _bind_path(registry, project_root, "SESSION_HANDOFF.md")
    report = _bind_path(report, project_root, "sprint_report.md")
    header = _read_header(header_file)
    section_raw, section_text = _read_utf8(section_file, "section file")
    _validate_input(section_text, "Live section")
    sections = _parse_sections(section_text)
    if (len(sections) != 1 or len(_top_level_headers(section_text)) != 1
            or section_text[:sections[0].start].strip()):
        raise RegistryError("Migration requires exactly one live section.")
    section = _selected_live(sections, sections[0].code, project_root)
    entry, _ = _read_utf8(entry_file, "report entry")
    _validated_entry(entry, section.code)
    with _exclusive_lock(registry), _exclusive_lock(report):
        _reject_multiple_links(registry, "registry")
        original, text = _read_utf8(registry, "legacy registry")
        if text.startswith("# SESSION_HANDOFF — "):
            current = _parse_sections(text)
            selected = _selected_live(current, section.code, project_root)
            selected_raw = text[selected.start:selected.end].encode("utf-8")
            prefix = section_raw
            if not selected_raw.startswith(prefix):
                raise RegistryError("Registry is already initialized; migration input does not match.")
            suffix = selected_raw[len(prefix):]
            if not re.match(rb"\n\n<!-- handoff-legacy-sha256:[a-f0-9]{64} -->\n", suffix):
                raise RegistryError("Registry already contains structured sections; no legacy migration permitted.")
            _append_once_locked(report, entry + suffix, section.code)
            return
        # Never classify a partial/old coded registry as an unstructured snapshot.
        if re.search(r"(?m)^\s*##\s+(?:\[closed(?:-pending)?\]|[🟢✅]|.*\bHO-)", text):
            raise RegistryError("Coded or malformed registry cannot be migrated as a legacy snapshot.")
        if not text.strip():
            raise RegistryError("Empty existing file is not a legacy snapshot.")
        block = _legacy_block(original)
        updated = header + _boundary_separator(header) + section_raw + block
        _parse_sections(updated.decode("utf-8"))
        _append_once_locked(report, entry + block, section.code)
        _atomic_replace(registry, updated)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RegistryError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="handoff-registry")
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init")
    initialize.add_argument("--registry", type=Path, required=True)
    initialize.add_argument("--project-root", type=Path, required=True)
    initialize.add_argument("--header-file", type=Path, required=True)

    migrate = commands.add_parser("migrate-legacy")
    for name in ("registry", "report", "project-root", "header-file", "section-file", "entry-file"):
        migrate.add_argument(f"--{name}", type=Path, required=True)

    get = commands.add_parser("get-live")
    get.add_argument("--registry", type=Path, required=True)
    get.add_argument("--project-root", type=Path, required=True)
    get.add_argument("--code", required=True)

    listing = commands.add_parser("list-live")
    listing.add_argument("--registry", type=Path, required=True)
    listing.add_argument("--project-root", type=Path, required=True)
    listing.add_argument("--json", action="store_true")

    insert = commands.add_parser("insert")
    insert.add_argument("--registry", type=Path, required=True)
    insert.add_argument("--section-file", type=Path, required=True)
    insert.add_argument("--project-root", type=Path, required=True)

    append = commands.add_parser("append-report")
    append.add_argument("--report", type=Path, required=True)
    append.add_argument("--entry-file", type=Path, required=True)
    append.add_argument("--project-root", type=Path, required=True)
    append.add_argument("--code", required=True)

    consume_command = commands.add_parser("consume")
    consume_command.add_argument("--registry", type=Path, required=True)
    consume_command.add_argument("--code", required=True)
    consume_command.add_argument("--project-root", type=Path, required=True)
    consume_command.add_argument("--date", required=True)
    consume_command.add_argument("--report", type=Path, required=True)

    purge_command = commands.add_parser("purge")
    purge_command.add_argument("--registry", type=Path, required=True)
    purge_command.add_argument("--project-root", type=Path, required=True)
    purge_command.add_argument("--code")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _build_parser().parse_args(argv)
        if hasattr(arguments, "registry"):
            _bind_path(arguments.registry, arguments.project_root, "SESSION_HANDOFF.md")
        if hasattr(arguments, "report"):
            _bind_path(arguments.report, arguments.project_root, "sprint_report.md")
        if arguments.command == "list-live":
            result = list_live(arguments.registry, arguments.project_root)
            if arguments.json:
                print(json.dumps(result, ensure_ascii=True))
            else:
                for section in result:
                    print("\t".join(json.dumps(section[key], ensure_ascii=True)
                                    for key in ("code", "workstream", "next_step")))
        elif arguments.command == "get-live":
            print(json.dumps(get_live(arguments.registry, arguments.code, arguments.project_root), ensure_ascii=True))
        elif arguments.command == "init":
            init_registry(arguments.registry, arguments.header_file, arguments.project_root)
        elif arguments.command == "migrate-legacy":
            migrate_legacy(arguments.registry, arguments.report, arguments.header_file,
                           arguments.section_file, arguments.entry_file, arguments.project_root)
        elif arguments.command == "insert":
            _, section_text = _read_utf8(arguments.section_file, "section file")
            _validate_input(section_text, "Live section")
            insert_section(arguments.registry, arguments.section_file, arguments.project_root)
        elif arguments.command == "append-report":
            append_report_once(arguments.report, arguments.entry_file, arguments.code)
        elif arguments.command == "consume":
            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", arguments.date) is None:
                    raise ValueError
                consumed_on = date.fromisoformat(arguments.date)
            except ValueError as error:
                raise RegistryError(f"Invalid ISO date '{arguments.date}'.") from error
            consume_with_report(arguments.registry, arguments.report, arguments.code,
                                arguments.project_root, consumed_on)
        elif arguments.command == "purge":
            print(purge(arguments.registry, arguments.project_root, arguments.code))
        return 0
    except (RegistryError, OSError) as error:
        message = str(error).encode("unicode_escape").decode("ascii")
        print(f"error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
