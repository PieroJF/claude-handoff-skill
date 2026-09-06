"""Documentation contracts for independently scoped runtime capabilities."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeContractTests(unittest.TestCase):
    def test_supplement_entries_preserve_original_code_and_use_unique_append_identity(self):
        protocol = (ROOT / "references" / "shared-protocol.md").read_text(encoding="utf-8")
        self.assertIn("**Handoff relacionado:** ORIGINAL_CODE", protocol)
        self.assertIn("unique report-only code", protocol)
        self.assertIn("Do not reuse the original `--code` for different content", protocol)

    def read_reference(self, name: str) -> str:
        path = ROOT / "references" / name
        self.assertTrue(path.is_file(), f"Missing runtime reference: {path.name}")
        return path.read_text(encoding="utf-8")

    def test_codex_maps_tasks_separately_from_subagents(self):
        text = self.read_reference("codex-runtime.md")
        for tool in ("list_threads", "read_thread", "send_message_to_thread", "wait_threads", "set_thread_title"):
            self.assertIn(f"mcp__codex_app__{tool}", text)
        self.assertIn("collaboration.list_agents", text)
        self.assertIn("collaboration.followup_task", text)
        self.assertIn("current task tree", text)
        self.assertIn("not interchangeable", text)

    def test_codex_uses_discovered_schemas_and_rejects_checkout_handoff(self):
        text = self.read_reference("codex-runtime.md")
        self.assertIn("schema", text)
        self.assertIn("handoff_thread", text)
        self.assertIn("checkout", text)
        self.assertIn("Do not call", text)
        executable = "\n".join(re.findall(r"```[^\n]*\n(.*?)```", text, re.S))
        for invalid in ("ToolSearch", "ListAgents", "SendMessage", "mcp__codex_app__handoff_thread"):
            self.assertNotIn(invalid, executable)

    def test_claude_inventory_and_team_boundary_are_explicit(self):
        text = self.read_reference("claude-runtime.md")
        self.assertIn("claude agents --help", text)
        self.assertIn("claude agents --json --cwd", text)
        self.assertIn("interactive", text)
        self.assertIn("SendMessage", text)
        self.assertIn("enabled Agent Teams", text)
        self.assertIn("known teammate", text)
        self.assertIn("no global", text)
        self.assertIn("local disk", text)

    def test_notifications_cannot_undo_persistence(self):
        text = self.read_reference("shared-protocol.md")
        self.assertIn("explicit user authorization", text)
        self.assertIn("notification failure", text)
        self.assertIn("never rolls back", text)
        self.assertIn("do not wait", text)

    def test_shared_protocol_documents_every_supported_cli_operation(self):
        text = self.read_reference("shared-protocol.md")
        contracts = (
            "init --registry PATH --project-root ROOT --header-file HEADER",
            "list-live --registry PATH --project-root ROOT --json",
            "get-live --registry PATH --project-root ROOT --code CODE",
            "insert --registry PATH --project-root ROOT --section-file SECTION",
            "append-report --report PATH --project-root ROOT --entry-file ENTRY --code CODE",
            "consume --registry PATH --project-root ROOT --report PATH --code CODE --date YYYY-MM-DD",
            "purge --registry PATH --project-root ROOT [--code CODE]",
            "migrate-legacy --registry PATH --project-root ROOT --report PATH --header-file HEADER --section-file SECTION --entry-file ENTRY",
        )
        for command in contracts:
            self.assertIn(command, text)
        self.assertIn("ROOT/SESSION_HANDOFF.md", text)
        self.assertIn("ROOT/sprint_report.md", text)

    def test_shared_protocol_preserves_resume_and_migration_detail(self):
        text = self.read_reference("shared-protocol.md")
        for contract in ("full section", "report before", "exact code", "same input files", "unstructured legacy", "UTF-8", "fingerprint", "no resurrection"):
            self.assertIn(contract, text)
        self.assertNotIn("from scripts.handoff_registry import consume", text)
        self.assertNotRegex(text, r"(?m)^\s*(?:printf|echo|Add-Content).*sprint_report")


if __name__ == "__main__":
    unittest.main()
