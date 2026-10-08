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
    """Return requested targets in CLI/GUI order for shared build entry points."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=(*TARGETS, "all"), default="all",
                        help="Build/package the CLI, GUI, or both (default)")
    target = parser.parse_args().target
    return TARGETS if target == "all" else (target,)


def executable_name(target):
    """Keep the GUI suffix consistent across compilation, archives, and smoke tests."""
    name = "smi2ass-gui" if target == "gui" else "smi2ass"
    return name + (".exe" if os.name == "nt" else "")


def archive_name(target):
    """Name native archives independently for each program and operating system."""
    program = "smi2ass-gui" if target == "gui" else "smi2ass"
    platform = "windows" if os.name == "nt" else "linux"
    return f"{program}_{platform}_x86-64"


def project_version():
    """Use package metadata as the single version source for build provenance."""
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def smoke_test(target, binary):
    """Exercise the selected executable with its matching installed-program checks."""
    script = "smoke_gui.py" if target == "gui" else "smoke_test.py"
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / script),
                    "--executable", str(binary)], check=True)
