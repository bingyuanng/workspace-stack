"""Exercise filesystem changes in temporary homes, without harness credentials."""

import os
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.repo = self.base / "stack with spaces"
        self.repo.mkdir()
        for directory in ["skills", "preferences", "scripts"]:
            shutil.copytree(install.ROOT / directory, self.repo / directory, ignore=shutil.ignore_patterns("__pycache__"))
        self.env = os.environ.copy()
        for key in ["XDG_CONFIG_HOME", "CODEX_HOME", "CLAUDE_CONFIG_DIR"]:
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home))
        self.instructions = self.home / ".config/opencode/AGENTS.md"
        self.skill = self.home / ".config/opencode/skills/general-writing"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, success=True):
        result = subprocess.run(
            [sys.executable, str(self.repo / "scripts/install.py"), *args],
            env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_preview_has_no_side_effects(self):
        self.run_cli("--harness", "opencode")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_preserve_existing_files_and_repeat_install(self):
        original = b"# Existing rules\r\nKeep my formatting."
        self.write(self.instructions, original)
        unrelated = self.skill.parent / "existing/SKILL.md"
        self.write(unrelated, b"---\nname: existing\n---\nExisting skill")
        self.run_cli("--harness", "opencode", "--apply")
        installed = self.instructions.read_bytes()
        self.assertTrue(installed.startswith(original))
        self.assertIn(str(self.repo).encode(), installed)
        self.assertNotIn(b"{{STACK_ROOT}}", installed)
        self.assertEqual(self.skill.resolve(), self.repo / "skills/general-writing")
        self.assertEqual(unrelated.read_bytes(), b"---\nname: existing\n---\nExisting skill")
        backups = list(self.instructions.parent.glob("*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.run_cli("--harness", "opencode", "--apply")
        self.assertEqual(self.instructions.read_bytes(), installed)
        self.assertEqual(len(list(self.instructions.parent.glob("*.bak"))), 1)

    def test_updates_only_managed_block(self):
        self.write(self.instructions, b"Existing rules")
        self.run_cli("--harness", "opencode", "--apply")
        with self.instructions.open("ab") as stream:
            stream.write(b"\nLater user addition")
        preference = self.repo / "preferences/global.md"
        preference.write_text(preference.read_text() + "\nPrefer concise answers.\n")
        self.run_cli("--harness", "opencode", "--apply")
        text = self.instructions.read_text()
        self.assertTrue(text.startswith("Existing rules"))
        self.assertTrue(text.endswith("\nLater user addition"))
        self.assertIn("Prefer concise answers.", text)
        self.assertEqual(text.count(install.START), 1)

    def test_name_conflict_aborts_before_any_changes(self):
        for location in [self.skill, self.home / ".agents/skills/different-folder"]:
            with self.subTest(location=location):
                self.write(location / "SKILL.md", b"---\nname: general-writing\n---\nKeep me")
                self.run_cli("--harness", "opencode", "--apply", success=False)
                self.assertFalse(self.instructions.exists())
                self.assertEqual((location / "SKILL.md").read_bytes(), b"---\nname: general-writing\n---\nKeep me")
                shutil.rmtree(location)

    def test_broken_skill_link_is_not_overwritten(self):
        self.skill.parent.mkdir(parents=True)
        self.skill.symlink_to(self.home / "missing", target_is_directory=True)
        self.run_cli("--harness", "opencode", "--apply", success=False)
        self.assertTrue(self.skill.is_symlink())
        self.assertFalse(self.instructions.exists())

    def test_compatibility_skill_symlink_conflict(self):
        other = self.home / "external-skill"
        self.write(other / "SKILL.md", b"---\nname: general-writing\n---\nExternal skill")
        link = self.home / ".agents/skills/other-name"
        link.parent.mkdir(parents=True)
        link.symlink_to(other, target_is_directory=True)
        self.run_cli("--harness", "opencode", "--apply", success=False)
        self.assertFalse(self.instructions.exists())
        self.assertTrue(link.is_symlink())

    def test_removal_restores_original_and_preserves_later_edits(self):
        original = b"Existing rules without trailing newline"
        self.write(self.instructions, original)
        self.run_cli("--harness", "opencode", "--apply")
        with self.instructions.open("ab") as stream:
            stream.write(b"\nUser addition")
        self.run_cli("--harness", "opencode", "--remove", "--apply")
        self.assertEqual(self.instructions.read_bytes(), original + b"\nUser addition")
        self.assertFalse(self.skill.is_symlink())

    def test_removal_deletes_created_instruction_file(self):
        self.run_cli("--harness", "opencode", "--apply")
        self.run_cli("--harness", "opencode", "--remove", "--apply")
        self.assertFalse(self.instructions.exists())

    def test_removal_keeps_skill_replaced_by_user(self):
        self.run_cli("--harness", "opencode", "--apply")
        self.skill.unlink()
        self.write(self.skill / "SKILL.md", b"User replacement")
        self.run_cli("--harness", "opencode", "--remove", "--apply")
        self.assertEqual((self.skill / "SKILL.md").read_bytes(), b"User replacement")

    def test_malformed_markers_abort(self):
        self.write(self.instructions, install.START.encode())
        self.run_cli("--harness", "opencode", "--apply", success=False)
        self.assertFalse(self.skill.exists())

    def test_fallback_is_not_silently_hidden(self):
        fallback = self.home / ".claude/CLAUDE.md"
        self.write(fallback, b"Existing Claude defaults")
        self.run_cli("--harness", "opencode", "--apply", success=False)
        self.assertFalse(self.instructions.exists())
        self.assertEqual(fallback.read_bytes(), b"Existing Claude defaults")

    def test_codex_uses_active_override(self):
        codex = self.home / ".codex"
        self.write(codex / "AGENTS.md", b"Base instructions")
        self.write(codex / "AGENTS.override.md", b"Active override")
        self.run_cli("--harness", "codex", "--apply")
        self.assertIn(install.START, (codex / "AGENTS.override.md").read_text())
        self.assertEqual((codex / "AGENTS.md").read_bytes(), b"Base instructions")
        self.assertTrue((self.home / ".agents/skills/general-writing").is_symlink())

    def test_empty_codex_override_stays_empty(self):
        override = self.home / ".codex/AGENTS.override.md"
        self.write(override, b"")
        self.run_cli("--harness", "codex", "--apply")
        self.assertEqual(override.read_bytes(), b"")
        self.assertIn(install.START, (override.parent / "AGENTS.md").read_text())

    def test_claude_and_custom_adapters(self):
        self.run_cli("--harness", "claude", "--apply")
        self.assertIn(install.START, (self.home / ".claude/CLAUDE.md").read_text())
        self.assertTrue((self.home / ".claude/skills/general-writing").is_symlink())
        custom = self.home / "other"
        self.run_cli("--harness", "custom", "--instructions-file", str(custom / "RULES.md"),
                     "--skills-dir", str(custom / "skills"), "--apply")
        self.assertIn(install.START, (custom / "RULES.md").read_text())
        self.assertTrue((custom / "skills/general-writing").is_symlink())

    def test_custom_environment_paths(self):
        self.env["XDG_CONFIG_HOME"] = str(self.home / "xdg")
        self.run_cli("--harness", "opencode", "--apply")
        self.assertTrue((self.home / "xdg/opencode/AGENTS.md").exists())
        self.env["CODEX_HOME"] = str(self.home / "codex-config")
        self.run_cli("--harness", "codex", "--apply")
        self.assertTrue((self.home / "codex-config/AGENTS.md").exists())

    def test_instruction_symlink_is_preserved(self):
        real_file = self.home / "dotfiles/AGENTS.md"
        self.write(real_file, b"Existing instructions")
        self.instructions.parent.mkdir(parents=True)
        self.instructions.symlink_to(real_file)
        self.run_cli("--harness", "opencode", "--apply")
        self.assertTrue(self.instructions.is_symlink())
        self.assertIn(install.START, real_file.read_text())
        self.run_cli("--harness", "opencode", "--remove", "--apply")
        self.assertTrue(self.instructions.is_symlink())
        self.assertEqual(real_file.read_bytes(), b"Existing instructions")

    def test_symlink_failure_leaves_instructions_unchanged(self):
        import argparse
        self.write(self.instructions, b"Keep this")
        args = argparse.Namespace(harness="opencode", instructions_file=None, skills_dir=None, apply=True, remove=False)
        with patch.dict(os.environ, self.env, clear=True), patch.object(install, "ROOT", self.repo), contextlib.redirect_stdout(io.StringIO()):
            with patch.object(Path, "symlink_to", side_effect=OSError("symlinks unavailable")):
                with self.assertRaises(OSError):
                    install.install(args)
        self.assertEqual(self.instructions.read_bytes(), b"Keep this")


if __name__ == "__main__":
    unittest.main()
