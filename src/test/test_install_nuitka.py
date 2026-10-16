"""Check compiler refresh and the temporary upstream hotfix fallback."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
try:
    import install_nuitka
finally:
    sys.path.pop(0)


class InstallNuitkaTest(unittest.TestCase):
    """Verify newer releases stay unpinned and failed installations stop builds."""

    def test_affected_release_uses_official_hotfix(self):
        """Replace 4.3 after querying the index, including normalized 4.3.0."""
        for affected in ("4.3", "4.3.0"):
            with self.subTest(version=affected), \
                 patch.object(install_nuitka, "version", side_effect=[affected, "4.3.1"]), \
                 patch.object(install_nuitka.subprocess, "run") as run:
                install_nuitka.main()
                self.assertEqual(2, run.call_count)
                self.assertEqual("nuitka", run.call_args_list[0].args[0][-1])
                self.assertEqual(install_nuitka.HOTFIX_URL, run.call_args_list[1].args[0][-1])

    def test_newer_release_is_not_replaced(self):
        """Keep upgrading through pip without selecting the older source hotfix."""
        for selected in ("4.3.1", "4.4", "5.0"):
            with self.subTest(version=selected), \
                 patch.object(install_nuitka, "version", return_value=selected), \
                 patch.object(install_nuitka.subprocess, "run") as run:
                install_nuitka.main()
                run.assert_called_once_with(
                    [sys.executable, "-I", "-m", "pip", "--isolated", "install", "--upgrade", "nuitka"],
                    check=True,
                )

    def test_failed_hotfix_stops_build(self):
        """Propagate install failures instead of compiling with the broken version."""
        failure = subprocess.CalledProcessError(1, ["pip"])
        with patch.object(install_nuitka, "version", return_value="4.3"), \
             patch.object(install_nuitka.subprocess, "run", side_effect=[None, failure]):
            with self.assertRaises(subprocess.CalledProcessError):
                install_nuitka.main()

    def test_ineffective_hotfix_stops_build(self):
        """Detect an installation that reports success but leaves 4.3 installed."""
        with patch.object(install_nuitka, "version", return_value="4.3"), \
             patch.object(install_nuitka.subprocess, "run"):
            with self.assertRaisesRegex(RuntimeError, "remains installed"):
                install_nuitka.main()


if __name__ == "__main__":
    unittest.main()
