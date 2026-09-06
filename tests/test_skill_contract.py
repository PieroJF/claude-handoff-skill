"""Entrypoint, templates, and Codex metadata form one portable skill contract."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        path = ROOT / relative
        self.assertTrue(path.is_file(), f"Missing skill resource: {relative}")
        return path.read_text(encoding="utf-8")

    def test_entrypoint_routes_to_existing_references(self):
        text = self.read("SKILL.md")
        self.assertLess(len(text.split()), 700)
        for name in ("shared-protocol", "codex-runtime", "claude-runtime"):
            target = f"references/{name}.md"
            self.assertIn(target, text)
            self.read(target)
        self.assertIn("scripts/handoff_registry.py", text)

    def test_entrypoint_preserves_mode_and_root_gates(self):
        text = self.read("SKILL.md")
        for mode in ("/handoff", "/handoff resume", "/handoff purge", "/handoff sessions"):
            self.assertIn(mode, text)
        for contract in ("before loading", "project root", "Codex tasks", "subagents", "Claude teams", "explicit user authorization", "verify"):
            self.assertIn(contract, text)
        for obsolete in ("ToolSearch", "ListAgents", "printf '%s'", "SendMessage"):
            self.assertNotIn(obsolete, text)

    def test_header_and_section_are_separate_inputs(self):
        header = self.read("templates/session_handoff_header.md")
        section = self.read("templates/session_handoff_section.md")
        self.assertTrue(header.startswith("# SESSION_HANDOFF — "))
        self.assertNotRegex(header, r"(?m)^## ")
        self.assertTrue(section.startswith("## [closed-pending] 🟢 "))
        self.assertNotIn("# SESSION_HANDOFF", section)
        self.assertEqual(len(re.findall(r"(?m)^## ", section)), 1)
        for required in ("> Proyecto:", " · raíz:", "> Canal:", "### Siguiente paso concreto", "- **Descripción:**"):
            self.assertIn(required, section)
        self.assertNotIn("ListAgents", section)

    def test_report_template_has_no_unfilled_rescue_section(self):
        text = self.read("templates/sprint_report_entry.md")
        self.assertIn("**Código de handoff:**", text)
        self.assertNotRegex(text, r"(?m)^#{3,4} Rescatado por canal.*\{\{")
        self.assertNotRegex(text, r"(?m)^Fuente: \{\{")
        self.assertIn("only when", text)
        self.assertIn("N/A", text)

    def test_codex_metadata_allows_implicit_invocation(self):
        text = self.read("agents/openai.yaml")
        self.assertIn('display_name: "Handoff"', text)
        self.assertIn("$handoff", text)
        self.assertIn("allow_implicit_invocation: true", text)
        short = re.search(r'short_description: "([^"\n]+)"', text)
        self.assertIsNotNone(short)
        self.assertTrue(25 <= len(short.group(1)) <= 64)

    def test_compatibility_pointer_and_readme_are_dual_runtime(self):
        pointer = self.read("cross-session.md")
        self.assertLess(len(pointer.split()), 220)
        for target in ("shared-protocol.md", "codex-runtime.md", "claude-runtime.md"):
            self.assertIn(target, pointer)
        readme = self.read("README.md")
        self.assertIn("Codex", readme)
        self.assertIn("Claude Code", readme)
        self.assertIn(".agents", readme)
        self.assertIn("junction", readme)
        self.assertIn("unittest discover", readme)


if __name__ == "__main__":
    unittest.main()
