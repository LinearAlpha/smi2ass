"""Shared target names and verification for native builds and archives."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
# All-target builds keep this order; each compiler consumes the available CPUs in turn.
TARGETS = ("cli", "gui")


def selected_targets():
    """Return requested targets in CLI/GUI order for shared build entry points.

    Returns:
        tuple[str, ...]: Requested targets in CLI/GUI build order.

    Raises:
        SystemExit: Arguments are invalid or help was requested.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=(*TARGETS, "all"), default="all",
                        help="Build/package the CLI, GUI, or both (default)")
    target = parser.parse_args().target
    return TARGETS if target == "all" else (target,)


def executable_name(target):
    """Keep target executable names consistent across builds and downloads.

    Args:
        target (str): Build target: cli or gui.

    Returns:
        str: Program name with the Windows .exe suffix when applicable.
    """
    name = "smi2ass-gui" if target == "gui" else "smi2ass"
    return name + (".exe" if os.name == "nt" else "")


def archive_name(target):
    """Name native archives independently for each program and operating system.

    Args:
        target (str): Build target: cli or gui.

    Returns:
        str: Archive basename containing the program, OS, and architecture.
    """
    program = "smi2ass-gui" if target == "gui" else "smi2ass"
    platform = "windows" if os.name == "nt" else "linux"
    return f"{program}_{platform}_x86-64"


def project_version():
    """Use package metadata as the single version source for build provenance.

    Returns:
        str: Release version declared in pyproject.toml.

    Raises:
        OSError: Project metadata cannot be read.
    """
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def smoke_test(target, binary):
    """Exercise the selected executable with its matching installed-program checks.

    Args:
        target (str): Target selecting CLI or GUI checks.
        binary (Path): Executable to launch and verify.

    Raises:
        subprocess.CalledProcessError: The selected smoke test exits unsuccessfully.
    """
    script = "smoke_gui.py" if target == "gui" else "smoke_test.py"
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / script),
                    "--executable", str(binary)], check=True)
