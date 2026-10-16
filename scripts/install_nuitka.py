"""Refresh Nuitka, using its official hotfix when PyPI still supplies 4.3."""
from importlib.metadata import version
import subprocess
import sys


# Official 4.3.1 tag, resolved to an immutable commit. Its PySide6 probe keeps
# bound callbacks alive; 4.3 can crash before the application window appears.
# https://nuitka.net/changelog/Changelog-next.html
HOTFIX_URL = (
    "https://github.com/Nuitka/Nuitka/archive/"
    "8ba9ccdf78268aba8bb21b79ed72fc9a4d44887d.zip"
)


def main():
    """Install the latest compiler and replace only the affected 4.3 release.

    Newer index releases remain eligible on every build. The source fallback
    can be removed once the package index provides the official 4.3.1 hotfix.

    Raises:
        subprocess.CalledProcessError: Either compiler installation fails.
        RuntimeError: The hotfix did not replace the affected compiler.
    """
    pip = [sys.executable, "-I", "-m", "pip", "--isolated", "install", "--upgrade"]
    subprocess.run(pip + ["nuitka"], check=True)
    selected = version("Nuitka")
    if selected in ("4.3", "4.3.0"):
        print("Nuitka 4.3 has a PySide6 startup bug; installing the official 4.3.1 hotfix.", flush=True)
        subprocess.run(pip + [HOTFIX_URL], check=True)
        selected = version("Nuitka")
        if selected in ("4.3", "4.3.0"):
            raise RuntimeError("Nuitka 4.3 remains installed after the hotfix installation.")
    print(f"Build compiler: Nuitka {selected}", flush=True)


if __name__ == "__main__":
    main()
