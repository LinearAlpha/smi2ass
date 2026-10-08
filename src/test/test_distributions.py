"""Regression checks for installing artifacts from a populated local checkout."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_distributions.py"
SMOKE = ROOT / "scripts" / "smoke_test.py"


class DistributionCheckTest(unittest.TestCase):
    """Reproduce polluted build environments without downloading runtime dependencies."""

    def test_installs_artifact_despite_inherited_same_version_metadata(self):
        checker = runpy.run_path(str(CHECKER))
        check_distribution = checker["check_distribution"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = "smi2ass-1.5.dist-info"
            metadata_text = "Metadata-Version: 2.1\nName: smi2ass\nVersion: 1.5\n"
            checkout = root / "checkout"
            (checkout / metadata).mkdir(parents=True)
            (checkout / metadata / "METADATA").write_text(metadata_text)
            (checkout / "smi2ass").mkdir()
            (checkout / "smi2ass" / "__init__.py").write_text(
                "raise RuntimeError('Imported checkout instead of artifact')\n")
            wheel = root / "smi2ass-1.5-py3-none-any.whl"
            # This dependency-free synthetic wheel tests installer isolation, not release content.
            # Keep its 1.5 version paired with the deliberately conflicting checkout metadata.
            files = {
                "smi2ass/__init__.py": "def main():\n    print('smi2ass 1.5')\n",
                "smi2ass/__main__.py": "from . import main\nmain()\n",
                f"{metadata}/METADATA": metadata_text,
                f"{metadata}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
                f"{metadata}/entry_points.txt": "[console_scripts]\nsmi2ass = smi2ass:main\n",
            }
            files[f"{metadata}/RECORD"] = ("".join(f"{name},,\n" for name in files)
                                           + f"{metadata}/RECORD,,\n")
            with zipfile.ZipFile(wheel, "w") as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
            scripts = root / "scripts"
            # Verify both module and console entry points resolve inside the fresh environment.
            scripts.mkdir()
            (scripts / "smoke_test.py").write_text(
                "import argparse, pathlib, subprocess, sys\n"
                "import smi2ass\n"
                "assert pathlib.Path(smi2ass.__file__).is_relative_to(pathlib.Path(sys.prefix))\n"
                "parser = argparse.ArgumentParser()\n"
                "parser.add_argument('--executable')\n"
                "args = parser.parse_args()\n"
                "command = [args.executable] if args.executable else [sys.executable, '-I', '-m', 'smi2ass']\n"
                "result = subprocess.run(command + ['--version'], check=True, capture_output=True, text=True)\n"
                "assert result.stdout.strip() == 'smi2ass 1.5'\n")
            with mock.patch.dict(os.environ, {"PYTHONPATH": str(checkout),
                                              "PIP_TARGET": str(root / "wrong-target")}):
                # This is the same-version metadata that can make pip skip a wheel.
                probe = subprocess.run(
                    [sys.executable, "-c", "from importlib.metadata import version; print(version('smi2ass'))"],
                    check=True, cwd=root, capture_output=True, text=True)
                self.assertEqual("1.5", probe.stdout.strip())
                with mock.patch.dict(check_distribution.__globals__, {"ROOT": root}):
                    check_distribution(wheel)
            self.assertFalse((root / "wrong-target").exists())

    def test_failed_smoke_command_displays_cli_output(self):
        error = subprocess.CalledProcessError(
            1, [sys.executable, "-m", "smi2ass"],
            output="CLI stdout\n", stderr="Original CLI failure\n")
        output = io.StringIO()
        with mock.patch.object(sys, "argv", [str(SMOKE)]), \
             mock.patch("subprocess.run", side_effect=error), \
             contextlib.redirect_stderr(output):
            with self.assertRaises(subprocess.CalledProcessError):
                runpy.run_path(str(SMOKE), run_name="__main__")
        self.assertIn("CLI stdout", output.getvalue())
        self.assertIn("Original CLI failure", output.getvalue())


if __name__ == "__main__":
    unittest.main()
