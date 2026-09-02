from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date
from pathlib import Path
import shutil
import tempfile
import threading
import unittest


_REGISTRY_IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from scripts.handoff_registry import (
        RegistryError,
        append_report,
        consume,
        insert_section,
        list_live,
        purge,
    )
except ModuleNotFoundError as error:
    if error.name not in {"scripts", "scripts.handoff_registry"}:
        raise
    _REGISTRY_IMPORT_ERROR = error
    RegistryError = RuntimeError


class HandoffRegistryTests(unittest.TestCase):
    FIXTURES = Path(__file__).with_name("fixtures")
    ALPHA_CODE = "HO-20260902-almanac-0915"
    BETA_CODE = "HO-20260902-borealis-1030"
    ARCHIVE_CODE = "HO-20260901-archive-0800"
    ALPHA_ROOT = Path(r"C:\HandoffContractFixtures\Atlas")
    BETA_ROOT = Path(r"C:\HandoffContractFixtures\Borealis")

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.workdir = Path(self._temporary_directory.name)
        self.registry = self.workdir / "SESSION_HANDOFF.md"
        shutil.copyfile(self.FIXTURES / "registry-two-live.md", self.registry)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def _require_implementation(self) -> None:
        if _REGISTRY_IMPORT_ERROR is not None:
            self.fail(
                "scripts.handoff_registry is not implemented; "
                "Task 6 must provide the shared registry API."
            )

    def _write_live_section(
        self,
        filename: str,
        code: str,
        workstream: str,
        project_root: Path,
        next_step: str,
    ) -> Path:
        section = self.workdir / filename
        section.write_text(
            "\n".join(
                (
                    f"## [closed-pending] 🟢 {code} — {workstream}",
                    "",
                    f"> Proyecto: {workstream.title()} Fixture · raíz: {project_root}",
                    "> Canal: test-writer [fixture-test] · capturado 2026-09-02 11:00",
                    "",
                    "### Estado actual del workstream",
                    "",
                    f"The {workstream} handoff is ready for its next step.",
                    "",
                    "### Siguiente paso concreto",
                    "",
                    f"- **Descripción:** {next_step}",
                    "",
                )
            ),
            encoding="utf-8",
            newline="\n",
        )
        return section

    def test_lists_only_live_sections(self):
        self._require_implementation()

        live_sections = list_live(self.registry, self.ALPHA_ROOT)

        self.assertEqual([section["code"] for section in live_sections], [self.ALPHA_CODE])
        self.assertEqual(live_sections[0]["workstream"], "almanac")
        self.assertEqual(
            Path(live_sections[0]["project_root"]).resolve(), self.ALPHA_ROOT.resolve()
        )
        self.assertEqual(live_sections[0]["next_step"], "Run the contract verification.")

    def test_inserts_without_changing_existing_sections(self):
        self._require_implementation()
        original_bytes = self.registry.read_bytes()
        inserted_code = "HO-20260902-appendix-1100"
        section_file = self._write_live_section(
            "appendix-section.md",
            inserted_code,
            "appendix",
            self.ALPHA_ROOT,
            "Add the appendix evidence.",
        )

        insert_section(self.registry, section_file, self.ALPHA_ROOT)

        updated_bytes = self.registry.read_bytes()
        self.assertIn(original_bytes, updated_bytes)
        self.assertIn(inserted_code.encode("utf-8"), updated_bytes)
        self.assertEqual(
            [section["code"] for section in list_live(self.registry, self.ALPHA_ROOT)],
            [self.ALPHA_CODE, inserted_code],
        )

    def test_rejects_duplicate_live_code(self):
        self._require_implementation()
        original_bytes = self.registry.read_bytes()
        duplicate_section = self._write_live_section(
            "duplicate-section.md",
            self.ALPHA_CODE,
            "duplicate-almanac",
            self.ALPHA_ROOT,
            "This must never be inserted.",
        )

        with self.assertRaises(RegistryError):
            insert_section(self.registry, duplicate_section, self.ALPHA_ROOT)

        self.assertEqual(self.registry.read_bytes(), original_bytes)

    def test_rejects_wrong_project_root(self):
        self._require_implementation()
        original_bytes = self.registry.read_bytes()

        with self.assertRaises(RegistryError):
            consume(self.registry, self.ALPHA_CODE, self.BETA_ROOT, date(2026, 9, 2))

        self.assertEqual(self.registry.read_bytes(), original_bytes)

    def test_consumes_exact_code_to_one_line_tombstone(self):
        self._require_implementation()

        consume(
            self.registry,
            self.ALPHA_CODE,
            Path(str(self.ALPHA_ROOT).lower()),
            date(2026, 9, 2),
        )

        tombstone = (
            "## [closed] ✅ HO-20260902-almanac-0915 — almanac "
            "· consumido 2026-09-02 · detalle en sprint_report.md"
        )
        matching_lines = [
            line for line in self.registry.read_text(encoding="utf-8").splitlines()
            if self.ALPHA_CODE in line
        ]
        self.assertEqual(matching_lines, [tombstone])
        registry_text = self.registry.read_text(encoding="utf-8")
        self.assertNotIn("The almanac handoff is waiting", registry_text)
        self.assertIn(self.BETA_CODE, registry_text)

    def test_rejects_already_consumed_code(self):
        self._require_implementation()
        consume(self.registry, self.ALPHA_CODE, self.ALPHA_ROOT, date(2026, 9, 2))
        consumed_bytes = self.registry.read_bytes()

        with self.assertRaises(RegistryError):
            consume(self.registry, self.ALPHA_CODE, self.ALPHA_ROOT, date(2026, 9, 2))

        self.assertEqual(self.registry.read_bytes(), consumed_bytes)

    def test_purges_only_consumed_tombstones(self):
        self._require_implementation()

        removed = purge(self.registry, self.ALPHA_ROOT)

        registry_text = self.registry.read_text(encoding="utf-8")
        self.assertEqual(removed, 1)
        self.assertNotIn(self.ARCHIVE_CODE, registry_text)
        self.assertIn(self.ALPHA_CODE, registry_text)
        self.assertIn(self.BETA_CODE, registry_text)

    def test_append_report_preserves_existing_bytes(self):
        self._require_implementation()
        report = self.workdir / "sprint_report.md"
        shutil.copyfile(self.FIXTURES / "report-existing.md", report)
        existing_bytes = report.read_bytes()
        entry = self.workdir / "new-report-entry.md"
        entry.write_text(
            "## Sesión: 2026-09-02 — almanac handoff\n\n"
            "**Código de handoff:** HO-20260902-almanac-0915\n",
            encoding="utf-8",
            newline="\n",
        )

        append_report(report, entry)

        updated_bytes = report.read_bytes()
        self.assertEqual(updated_bytes[: len(existing_bytes)], existing_bytes)
        self.assertEqual(
            updated_bytes[len(existing_bytes) :],
            b"\n\n---\n\n" + entry.read_bytes(),
        )

    def test_concurrent_inserts_keep_both_sections(self):
        self._require_implementation()
        concurrent_root = self.workdir / "concurrent-project"
        concurrent_root.mkdir()
        self.registry.write_text(
            "# SESSION_HANDOFF — concurrent-fixture\n\n"
            "> Registry fixture for concurrent writes.\n",
            encoding="utf-8",
            newline="\n",
        )
        first_code = "HO-20260902-writer-one-1115"
        second_code = "HO-20260902-writer-two-1116"
        first_section = self._write_live_section(
            "writer-one.md",
            first_code,
            "writer-one",
            concurrent_root,
            "Keep writer one intact.",
        )
        second_section = self._write_live_section(
            "writer-two.md",
            second_code,
            "writer-two",
            concurrent_root,
            "Keep writer two intact.",
        )
        ready = threading.Barrier(2)

        def insert_after_barrier(section_file: Path) -> None:
            ready.wait(timeout=5)
            insert_section(self.registry, section_file, concurrent_root)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(insert_after_barrier, first_section),
                executor.submit(insert_after_barrier, second_section),
            ]
            completed, pending = wait(futures, timeout=10)
            self.assertEqual(pending, set())
            self.assertEqual(completed, set(futures))
            for future in futures:
                future.result()

        registry_bytes = self.registry.read_bytes()
        self.assertEqual(registry_bytes.count(first_code.encode("utf-8")), 1)
        self.assertEqual(registry_bytes.count(second_code.encode("utf-8")), 1)
        self.assertEqual(
            {section["code"] for section in list_live(self.registry, concurrent_root)},
            {first_code, second_code},
        )


if __name__ == "__main__":
    unittest.main()
