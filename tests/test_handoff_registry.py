from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import multiprocessing
import os
from pathlib import Path
import queue
import shutil
import sys
import tempfile
import time
import traceback
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

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


@contextmanager
def _hold_sidecar_lock(sidecar: Path):
    sidecar.touch(exist_ok=True)
    with sidecar.open("r+b") as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _insert_in_independent_process(
    registry: str,
    section_file: str,
    project_root: str,
    ready: multiprocessing.queues.Queue,
    release: multiprocessing.synchronize.Event,
    attempted: multiprocessing.queues.Queue,
    outcomes: multiprocessing.queues.Queue,
) -> None:
    try:
        from scripts.handoff_registry import insert_section as process_insert_section

        ready.put(os.getpid())
        if not release.wait(timeout=10):
            outcomes.put(("error", os.getpid(), "parent did not release the writers"))
            return
        attempted.put(os.getpid())
        process_insert_section(Path(registry), Path(section_file), Path(project_root))
        outcomes.put(("ok", os.getpid(), ""))
    except BaseException:
        outcomes.put(("error", os.getpid(), traceback.format_exc()))
        raise


class HandoffRegistryTests(unittest.TestCase):
    FIXTURES = Path(__file__).with_name("fixtures")
    ALPHA_CODE = "HO-20260902-almanac-0915"
    BETA_CODE = "HO-20260902-borealis-1030"
    ARCHIVE_CODE = "HO-20260901-archive-0800"
    ALPHA_ROOT = Path(r"C:\HandoffContractFixtures\Atlas")
    BETA_ROOT = Path(r"C:\HandoffContractFixtures\Borealis")
    REGISTRY_HEADER = (
        "# SESSION_HANDOFF — contract-fixture\n\n"
        "> Registry fixture for isolated handoff-registry contracts.\n\n"
    ).encode("utf-8")
    ALPHA_LIVE_SECTION = (
        "## [closed-pending] 🟢 HO-20260902-almanac-0915 — almanac\n\n"
        "> Proyecto: Atlas Fixture · raíz: C:\\HandoffContractFixtures\\Atlas\n"
        "> Canal: atlas-writer [fixture-a1] · capturado 2026-09-02 09:15\n\n"
        "### Estado actual del workstream\n\n"
        "The almanac handoff is waiting for its contract verification.\n\n"
        "### Siguiente paso concreto\n\n"
        "- **Descripción:** Run the contract verification.\n\n"
    ).encode("utf-8")
    BETA_LIVE_SECTION = (
        "## [closed-pending] 🟢 HO-20260902-borealis-1030 — borealis\n\n"
        "> Proyecto: Borealis Fixture · raíz: C:\\HandoffContractFixtures\\Borealis\n"
        "> Canal: borealis-writer [fixture-b2] · capturado 2026-09-02 10:30\n\n"
        "### Estado actual del workstream\n\n"
        "The borealis handoff must remain untouched by other workstreams.\n\n"
        "### Siguiente paso concreto\n\n"
        "- **Descripción:** Preserve the borealis state.\n\n"
    ).encode("utf-8")
    ARCHIVE_TOMBSTONE = (
        "## [closed] ✅ HO-20260901-archive-0800 — archive "
        "· consumido 2026-09-01 · detalle en sprint_report.md\n"
    ).encode("utf-8")
    ALPHA_TOMBSTONE = (
        "## [closed] ✅ HO-20260902-almanac-0915 — almanac "
        "· consumido 2026-09-02 · detalle en sprint_report.md\n\n"
    ).encode("utf-8")
    REGISTRY_BYTES = (
        REGISTRY_HEADER + ALPHA_LIVE_SECTION + BETA_LIVE_SECTION + ARCHIVE_TOMBSTONE
    )
    CONSUMED_REGISTRY_BYTES = (
        REGISTRY_HEADER + ALPHA_TOMBSTONE + BETA_LIVE_SECTION + ARCHIVE_TOMBSTONE
    )
    PURGED_REGISTRY_BYTES = REGISTRY_HEADER + ALPHA_LIVE_SECTION + BETA_LIVE_SECTION
    REPORT_EXISTING_BYTES = (
        "# Sprint report\n\n"
        "---\n\n"
        "## Sesión: 2026-09-01 — archive handoff\n\n"
        "**Código de handoff:** HO-20260901-archive-0800\n\n"
        "### Resultado\n\n"
        "The archived entry is immutable evidence and must survive every later append byte-for-byte.\n"
    ).encode("utf-8")
    REPORT_APPEND_ENTRY_BYTES = (
        "## Sesión: 2026-09-02 — almanac handoff\n\n"
        "**Código de handoff:** HO-20260902-almanac-0915\n"
    ).encode("utf-8")

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

    def _assert_registry_fixture_bytes(self) -> None:
        self.assertEqual(self.registry.read_bytes(), self.REGISTRY_BYTES)

    def _receive_messages(
        self,
        messages: multiprocessing.queues.Queue,
        count: int,
        timeout: float,
        description: str,
    ) -> list[object]:
        deadline = time.monotonic() + timeout
        received = []
        while len(received) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.fail(f"Timed out waiting for {description}.")
            try:
                received.append(messages.get(timeout=remaining))
            except queue.Empty:
                self.fail(f"Timed out waiting for {description}.")
        return received

    def _terminate_processes(self, processes: list[multiprocessing.Process]) -> None:
        for process in processes:
            if process.pid is not None:
                process.join(timeout=5)
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.terminate()
        for process in processes:
            if process.pid is not None and process.is_alive():
                process.join(timeout=5)

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
        self._assert_registry_fixture_bytes()

        live_sections = list_live(self.registry, self.ALPHA_ROOT)

        self.assertEqual([section["code"] for section in live_sections], [self.ALPHA_CODE])
        self.assertEqual(live_sections[0]["workstream"], "almanac")
        self.assertEqual(
            Path(live_sections[0]["project_root"]).resolve(), self.ALPHA_ROOT.resolve()
        )
        self.assertEqual(live_sections[0]["next_step"], "Run the contract verification.")

    def test_inserts_without_changing_existing_sections(self):
        self._require_implementation()
        self._assert_registry_fixture_bytes()
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
        self._assert_registry_fixture_bytes()
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
        self._assert_registry_fixture_bytes()
        original_bytes = self.registry.read_bytes()

        with self.assertRaises(RegistryError):
            consume(self.registry, self.ALPHA_CODE, self.BETA_ROOT, date(2026, 9, 2))

        self.assertEqual(self.registry.read_bytes(), original_bytes)

    def test_consumes_exact_code_to_one_line_tombstone(self):
        self._require_implementation()
        self._assert_registry_fixture_bytes()

        consume(
            self.registry,
            self.ALPHA_CODE,
            Path(str(self.ALPHA_ROOT).lower()),
            date(2026, 9, 2),
        )

        self.assertEqual(self.registry.read_bytes(), self.CONSUMED_REGISTRY_BYTES)

    def test_rejects_already_consumed_code(self):
        self._require_implementation()
        self._assert_registry_fixture_bytes()
        consume(self.registry, self.ALPHA_CODE, self.ALPHA_ROOT, date(2026, 9, 2))
        self.assertEqual(self.registry.read_bytes(), self.CONSUMED_REGISTRY_BYTES)

        with self.assertRaises(RegistryError):
            consume(self.registry, self.ALPHA_CODE, self.ALPHA_ROOT, date(2026, 9, 2))

        self.assertEqual(self.registry.read_bytes(), self.CONSUMED_REGISTRY_BYTES)

    def test_purges_only_consumed_tombstones(self):
        self._require_implementation()
        self._assert_registry_fixture_bytes()

        removed = purge(self.registry, self.ALPHA_ROOT)

        self.assertEqual(removed, 1)
        self.assertEqual(self.registry.read_bytes(), self.PURGED_REGISTRY_BYTES)

    def test_append_report_preserves_existing_bytes(self):
        self._require_implementation()
        report = self.workdir / "sprint_report.md"
        shutil.copyfile(self.FIXTURES / "report-existing.md", report)
        existing_bytes = report.read_bytes()
        self.assertEqual(existing_bytes, self.REPORT_EXISTING_BYTES)
        entry = self.workdir / "new-report-entry.md"
        entry.write_bytes(self.REPORT_APPEND_ENTRY_BYTES)

        append_report(report, entry)

        updated_bytes = report.read_bytes()
        self.assertEqual(
            updated_bytes,
            self.REPORT_EXISTING_BYTES
            + b"\n\n---\n\n"
            + self.REPORT_APPEND_ENTRY_BYTES,
        )

    def test_concurrent_inserts_keep_both_sections(self):
        self._require_implementation()
        self._assert_registry_fixture_bytes()
        concurrent_root = self.workdir / "concurrent-project"
        concurrent_root.mkdir()
        concurrent_header = (
            "# SESSION_HANDOFF — concurrent-fixture\n\n"
            "> Registry fixture for concurrent writes.\n"
        ).encode("utf-8")
        self.registry.write_bytes(concurrent_header)
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
        context = multiprocessing.get_context("spawn")
        ready = context.Queue()
        release = context.Event()
        attempted = context.Queue()
        outcomes = context.Queue()
        processes = [
            context.Process(
                target=_insert_in_independent_process,
                args=(
                    str(self.registry),
                    str(section_file),
                    str(concurrent_root),
                    ready,
                    release,
                    attempted,
                    outcomes,
                ),
            )
            for section_file in (first_section, second_section)
        ]
        lock_sidecar = self.registry.with_name(f"{self.registry.name}.lock")
        self.assertEqual(lock_sidecar.name, "SESSION_HANDOFF.md.lock")

        try:
            with _hold_sidecar_lock(lock_sidecar):
                for process in processes:
                    process.start()
                ready_processes = self._receive_messages(
                    ready, 2, 5, "both child processes to become ready"
                )
                self.assertEqual(set(ready_processes), {process.pid for process in processes})
                release.set()
                attempted_processes = self._receive_messages(
                    attempted, 2, 5, "both child processes to attempt insertion"
                )
                self.assertEqual(
                    set(attempted_processes), {process.pid for process in processes}
                )
                try:
                    early_outcome = outcomes.get(timeout=0.5)
                except queue.Empty:
                    early_outcome = None
                self.assertIsNone(
                    early_outcome,
                    "a writer completed while another process held the public lock sidecar",
                )
                self.assertEqual(self.registry.read_bytes(), concurrent_header)

            worker_outcomes = self._receive_messages(
                outcomes, 2, 10, "both child process outcomes after lock release"
            )
        finally:
            release.set()
            self._terminate_processes(processes)

        for process in processes:
            self.assertEqual(process.exitcode, 0, f"worker {process.pid} did not exit cleanly")
        self.assertEqual(
            sorted(worker_outcomes),
            sorted(("ok", process.pid, "") for process in processes),
        )

        registry_bytes = self.registry.read_bytes()
        self.assertEqual(registry_bytes.count(first_code.encode("utf-8")), 1)
        self.assertEqual(registry_bytes.count(second_code.encode("utf-8")), 1)
        self.assertEqual(
            {section["code"] for section in list_live(self.registry, concurrent_root)},
            {first_code, second_code},
        )


if __name__ == "__main__":
    unittest.main()
