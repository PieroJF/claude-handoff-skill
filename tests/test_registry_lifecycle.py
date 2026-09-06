"""Runtime-safe lifecycle operations; fixtures never use real project registries."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import handoff_registry as registry


class LifecycleTests(unittest.TestCase):
    CODE = "HO-20260906-legacy-1100"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "SESSION_HANDOFF.md"
        self.report = self.root / "sprint_report.md"
        self.header = self.write("header.md", "# SESSION_HANDOFF — Fixture\n\n> Registry.\n")
        self.section = self.write("section.md", (
            f"## [closed-pending] 🟢 {self.CODE} — legacy\n\n"
            f"> Proyecto: Fixture · raíz: {self.root}\n\n"
            "### Siguiente paso concreto\n\n- **Descripción:** Continue verified work.\n"
        ))
        self.entry = self.write("entry.md", (
            f"## Sesión: 2026-09-06 — Legacy\n\n**Código de handoff:** {self.CODE}\n\n"
            "### Resultado\n\nPreserved original work.\n"
        ))

    def write(self, name, text):
        path = self.root / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def api(self, name):
        self.assertTrue(callable(getattr(registry, name, None)), f"Missing lifecycle API: {name}")
        return getattr(registry, name)

    def init(self):
        return self.api("init_registry")(self.path, self.header, self.root)

    def migrate(self):
        return self.api("migrate_legacy")(
            self.path, self.report, self.header, self.section, self.entry, self.root
        )

    def test_init_is_idempotent_preserves_existing_and_rejects_legacy(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        before = self.path.read_bytes()
        self.init()
        self.assertEqual(self.path.read_bytes(), before)
        self.path.write_bytes(b"# Previous snapshot\nImportant work\n")
        with self.assertRaises(registry.RegistryError):
            self.init()
        self.assertIn(b"Important work", self.path.read_bytes())

    def test_init_rejects_header_with_sections_or_placeholders(self):
        for text in ["# SESSION_HANDOFF — {{project}}\n", "# SESSION_HANDOFF — X\n## Notes\n"]:
            self.header.write_text(text, encoding="utf-8")
            with self.assertRaises(registry.RegistryError):
                self.init()
            self.assertFalse(self.path.exists())

    def test_close_init_gate_detects_legacy_that_lists_as_empty(self):
        original = b"# Legacy session snapshot\nImportant unfinished work.\n"
        self.path.write_bytes(original)
        self.assertEqual(registry.list_live(self.path, self.root), [])
        with self.assertRaises(registry.RegistryError):
            self.init()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.report.exists())

    def test_get_live_returns_exact_whole_section_and_rejects_closed_or_wrong_root(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        get = self.api("get_live")
        self.assertEqual(get(self.path, self.CODE, self.root)["section"], self.section.read_text(encoding="utf-8"))
        with self.assertRaises(registry.RegistryError):
            get(self.path, self.CODE, self.root / "elsewhere")
        registry.consume(self.path, self.CODE, self.root, date(2026, 9, 6))
        with self.assertRaises(registry.RegistryError):
            get(self.path, self.CODE, self.root)

    def test_report_append_is_idempotent_and_rejects_conflicting_code(self):
        append = self.api("append_report_once")
        append(self.report, self.entry, self.CODE)
        before = self.report.read_bytes()
        append(self.report, self.entry, self.CODE)
        self.assertEqual(self.report.read_bytes(), before)
        self.entry.write_bytes(self.entry.read_bytes() + b"Changed detail\n")
        with self.assertRaises(registry.RegistryError):
            append(self.report, self.entry, self.CODE)
        self.assertEqual(self.report.read_bytes(), before)

    def test_report_retry_rejects_shortened_payload_for_same_code(self):
        append = self.api("append_report_once")
        append(self.report, self.entry, self.CODE)
        before = self.report.read_bytes()
        self.entry.write_bytes(self.entry.read_bytes().replace(b"Preserved original work.\n", b""))
        with self.assertRaises(registry.RegistryError):
            append(self.report, self.entry, self.CODE)
        self.assertEqual(self.report.read_bytes(), before)

    def test_consume_rejects_bare_report_marker_and_torn_or_changed_envelope(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        consume = self.api("consume_with_report")
        before = self.path.read_bytes()
        self.report.write_text(f"**Código de handoff:** {self.CODE}\n", encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            consume(self.path, self.report, self.CODE, self.root, date(2026, 9, 6))
        self.report.unlink()
        self.api("append_report_once")(self.report, self.entry, self.CODE)
        report = self.report.read_bytes()
        for broken in [report[:-8], report.replace(b"Preserved", b"Modified!")]:
            self.report.write_bytes(broken)
            with self.assertRaises(registry.RegistryError):
                consume(self.path, self.report, self.CODE, self.root, date(2026, 9, 6))
            self.assertEqual(self.path.read_bytes(), before)
    def test_consume_requires_real_unfenced_report_code_before_mutation(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        consume = self.api("consume_with_report")
        before = self.path.read_bytes()
        self.report.write_text(f"```md\n**Código de handoff:** {self.CODE}\n```\n", encoding="utf-8")
        with self.assertRaises(registry.RegistryError):
            consume(self.path, self.report, self.CODE, self.root, date(2026, 9, 6))
        self.assertEqual(self.path.read_bytes(), before)
        self.api("append_report_once")(self.report, self.entry, self.CODE)
        consume(self.path, self.report, self.CODE, self.root, date(2026, 9, 6))
        self.assertIn(b"[closed]", self.path.read_bytes())

    def test_migration_preserves_exact_legacy_and_retries_without_duplicate_report(self):
        original = b"# Legacy\r\nOld work\r\n```python\r\nprint('pending')\r\n"
        self.path.write_bytes(original)
        self.report.write_bytes(b"# Earlier history\nImmutable.\n")
        self.migrate()
        result, report = self.path.read_bytes(), self.report.read_bytes()
        self.assertIn(original, result)
        self.assertIn(original, report)
        self.assertTrue(report.startswith(b"# Earlier history\nImmutable.\n"))
        self.assertEqual(len(registry.list_live(self.path, self.root)), 1)
        self.migrate()
        self.assertEqual(self.path.read_bytes(), result)
        self.assertEqual(self.report.read_bytes(), report)

    def test_migration_report_survives_replace_failure_and_retry_is_idempotent(self):
        original = b"# Legacy\nUnfinished work\n"
        self.path.write_bytes(original)
        self.api("migrate_legacy")
        with patch.object(registry.os, "replace", side_effect=OSError("injected replacement failure")):
            with self.assertRaises(registry.RegistryError):
                self.migrate()
        self.assertEqual(self.path.read_bytes(), original)
        report = self.report.read_bytes()
        self.assertIn(original, report)
        self.migrate()
        self.assertEqual(self.report.read_bytes(), report)

    def test_migration_does_not_replace_if_report_fsync_fails(self):
        original = b"# Legacy\nUnfinished work\n"
        self.path.write_bytes(original)
        self.api("migrate_legacy")
        with patch.object(registry.os, "fsync", side_effect=OSError("injected flush failure")):
            with self.assertRaises(registry.RegistryError):
                self.migrate()
        self.assertEqual(self.path.read_bytes(), original)

    def test_migration_rejects_coded_or_malformed_registries(self):
        self.api("migrate_legacy")
        for text in [
            "## 🟢 HO-20200101-old-0000 — Old\n", "## [closed-pending] broken\n",
            "# SESSION_HANDOFF — Fixture\n\n> Registry\n", self.section.read_text(encoding="utf-8"),
        ]:
            self.path.write_text(text, encoding="utf-8")
            before = self.path.read_bytes()
            with self.assertRaises(registry.RegistryError):
                self.migrate()
            self.assertEqual(self.path.read_bytes(), before)
            self.assertFalse(self.report.exists())

    def test_cli_binds_purge_to_project_canonical_registry_even_without_live_sections(self):
        other = self.root / "other"
        other.mkdir()
        foreign = other / "SESSION_HANDOFF.md"
        original = (f"## [closed] ✅ {self.CODE} — legacy · consumido 2026-09-06 · detalle en sprint_report.md\n").encode("utf-8")
        foreign.write_bytes(original)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            status = registry.main(["purge", "--registry", str(foreign), "--project-root", str(self.root)])
        self.assertEqual(status, 2, "CLI must reject another project's registry")
        self.assertEqual(foreign.read_bytes(), original)

    def test_cli_get_live_json_includes_full_section(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            status = registry.main(["get-live", "--registry", str(self.path), "--project-root", str(self.root), "--code", self.CODE])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["section"], self.section.read_text(encoding="utf-8"))

    def test_independent_cli_processes_keep_init_and_report_idempotent(self):
        script = str(Path(registry.__file__).resolve())
        common = ["--project-root", str(self.root)]
        for arguments in [
            ["init", "--registry", str(self.path), "--header-file", str(self.header)] + common,
            ["append-report", "--report", str(self.report), "--entry-file", str(self.entry), "--code", self.CODE] + common,
        ]:
            processes = [subprocess.Popen([sys.executable, "-B", script, *arguments],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            for process in processes:
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, (stdout, stderr))
        self.assertEqual(self.path.read_bytes(), self.header.read_bytes())
        self.assertEqual(self.report.read_bytes().count(f"**Código de handoff:** {self.CODE}".encode("utf-8")), 1)

    def test_cli_get_live_json_works_with_windows_legacy_stdout_encoding(self):
        self.init()
        registry.insert_section(self.path, self.section, self.root)
        environment = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
        result = subprocess.run([sys.executable, "-B", str(Path(registry.__file__).resolve()),
                                 "get-live", "--registry", str(self.path), "--project-root", str(self.root),
                                 "--code", self.CODE], capture_output=True, timeout=15, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["section"], self.section.read_bytes().decode("utf-8"))

    def test_invalid_report_heading_is_rejected_before_append_and_can_retry(self):
        append = self.api("append_report_once")
        correct = self.entry.read_bytes()
        self.report.write_bytes(b"# Previous report\nPreserve these bytes.\n")
        before = self.report.read_bytes()
        self.entry.write_bytes(correct.replace("## Sesión:".encode("utf-8"), b"## Wrong:"))
        with self.assertRaises(registry.RegistryError):
            append(self.report, self.entry, self.CODE)
        self.assertEqual(self.report.read_bytes(), before)
        self.entry.write_bytes(correct)
        append(self.report, self.entry, self.CODE)
        self.assertIn(correct, self.report.read_bytes())

    def test_cli_lifecycle_reads_and_consumes_only_after_durable_report(self):
        script = str(Path(registry.__file__).resolve())
        common = ["--project-root", str(self.root)]
        def run(*args, expected=0):
            result = subprocess.run([sys.executable, "-B", script, *args, *common],
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, expected, result.stderr)
            return result.stdout
        run("init", "--registry", str(self.path), "--header-file", str(self.header))
        run("insert", "--registry", str(self.path), "--section-file", str(self.section))
        run("consume", "--registry", str(self.path), "--report", str(self.report), "--code", self.CODE,
            "--date", "2026-09-06", expected=2)
        run("append-report", "--report", str(self.report), "--entry-file", str(self.entry), "--code", self.CODE)
        self.assertEqual(len(json.loads(run("list-live", "--registry", str(self.path), "--json"))), 1)
        run("consume", "--registry", str(self.path), "--report", str(self.report), "--code", self.CODE, "--date", "2026-09-06")
        run("get-live", "--registry", str(self.path), "--code", self.CODE, expected=2)
        self.assertEqual(run("purge", "--registry", str(self.path), "--code", self.CODE).strip(), b"1")
        self.assertEqual(json.loads(run("list-live", "--registry", str(self.path), "--json")), [])


if __name__ == "__main__":
    unittest.main()
