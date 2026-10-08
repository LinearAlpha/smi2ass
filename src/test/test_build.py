"""Verify isolated native build targets and the contents of their archives."""
from importlib.util import find_spec
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
# These are checkout build tools, not part of the installed runtime package.
sys.path.insert(0, str(SCRIPTS))
try:
    import build_common
    import clean_project
    import build_executable
    if find_spec("py7zr"):
        import package_assets
finally:
    sys.path.pop(0)


class BuildTargetTest(unittest.TestCase):
    def test_cli_and_gui_builds_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src" / "setting").mkdir(parents=True)
            (root / "src" / "setting" / "ass_styles.json").write_text("{}")
            with patch.object(build_executable, "ROOT", root), \
                 patch.object(build_executable.subprocess, "run") as compile_run, \
                 patch.object(build_executable, "smoke_test") as smoke:
                build_executable.build_target("cli")
                build_executable.build_target("gui")
            cli, gui = [call.args[0] for call in compile_run.call_args_list]
            self.assertIn("--output-filename=" + build_common.executable_name("cli"), cli)
            self.assertIn("--output-filename=" + build_common.executable_name("gui"), gui)
            self.assertTrue(any("PySide6" in option for option in cli))
            self.assertNotIn("--enable-plugin=pyside6", cli)
            self.assertIn("--enable-plugin=pyside6", gui)
            self.assertEqual(os.name == "nt", "--windows-console-mode=disable" in gui)
            for target in ("cli", "gui"):
                self.assertTrue((root / "build" / target / "setting" / "ass_styles.json").exists())
            self.assertEqual(["cli", "gui"], [call.args[0] for call in smoke.call_args_list])

    @unittest.skipUnless(find_spec("py7zr"), "Install py7zr to test native archives")
    def test_archives_contain_only_the_corresponding_program_and_verify_both_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ("README.md", "LICENSE.txt", "CHANGELOG.md"):
                (root / filename).write_text(filename)
            for target in ("cli", "gui"):
                folder = root / "build" / target
                (folder / "setting").mkdir(parents=True)
                (folder / "setting" / "ass_styles.json").write_text("{}")
                (folder / build_common.executable_name(target)).write_text(target)
            seen = []

            def verify(target, binary):
                self.assertEqual(target, binary.read_text())
                self.assertEqual(build_common.executable_name(target), binary.name)
                self.assertEqual("{}", (binary.parent / "setting" / "ass_styles.json").read_text())
                seen.append((target, binary.parent.name))

            # Bound decompression memory for these small fixtures, including restricted test hosts.
            with patch.object(package_assets, "ROOT", root), \
                 patch.object(package_assets, "build_info", side_effect=lambda target: {"target": target}), \
                 patch.object(package_assets, "smoke_test", side_effect=verify), \
                 patch("py7zr.py7zr.get_memory_limit", return_value=32 * 1024**2):
                package_assets.package_target("cli")
                package_assets.package_target("gui")
            self.assertEqual([("cli", "zip"), ("cli", "7z"), ("gui", "zip"), ("gui", "7z")], seen)
            self.assertEqual(4, len(list((root / "release-assets").iterdir())))
            for target in ("cli", "gui"):
                archive = root / "release-assets" / (build_common.archive_name(target) + ".zip")
                with ZipFile(archive) as zipped:
                    binaries = {name for name in zipped.namelist() if name.startswith("smi2ass")}
                    self.assertEqual({build_common.executable_name(target)}, binaries)
                    self.assertEqual(target, json.loads(zipped.read("BUILD-INFO.json"))["target"])


class CleanProjectTest(unittest.TestCase):
    def test_clean_removes_generated_files_and_preserves_source_settings_and_venvs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = ["build/gui/smi2ass-gui", "dist/smi2ass.whl", "release-assets/archive.zip",
                         "smi2ass.egg-info/PKG-INFO", "src/smi2ass.egg-info/PKG-INFO",
                         "__pycache__/root.pyc", "src/test/__pycache__/test.pyc",
                         "scripts/__pycache__/build.pyc", ".pytest_cache/cache",
                         "nuitka-crash-report.xml"]
            preserved = ["src/smi2ass.py", "src/setting/lan_code.json", "scripts/build_executable.py",
                         "README.md", "input.smi", "output.ass", ".git/config",
                         ".venv/lib/__pycache__/keep.pyc", ".build-venv/bin/python",
                         ".wheel-venv/lib/keep.py", ".sdist-venv/lib/keep.py",
                         "src/.venv/lib/__pycache__/keep.pyc", "scripts/tools/pyvenv.cfg",
                         "scripts/tools/lib/__pycache__/keep.pyc"]
            for name in generated + preserved:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            removed = clean_project.clean_project(root)
            self.assertIn("build", removed)
            self.assertTrue(all(not (root / name).exists() for name in generated))
            for name in preserved:
                self.assertEqual(name, (root / name).read_text())
            self.assertEqual([], clean_project.clean_project(root))

    def test_clean_does_not_follow_links_to_files_outside_the_project(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            root.mkdir()
            outside = base / "outside"
            (outside / "__pycache__").mkdir(parents=True)
            sentinel = outside / "__pycache__" / "keep.pyc"
            sentinel.write_text("keep")
            try:
                (root / "build").symlink_to(outside, target_is_directory=True)
                (root / "src").symlink_to(outside, target_is_directory=True)
                (root / "scripts").mkdir()
                (root / "scripts" / "linked").symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Directory symlinks unavailable: {error}")
            clean_project.clean_project(root)
            self.assertEqual("keep", sentinel.read_text())
            self.assertFalse((root / "build").is_symlink())
            self.assertTrue((root / "src").is_symlink())
            self.assertTrue((root / "scripts" / "linked").is_symlink())


if __name__ == "__main__":
    unittest.main()
