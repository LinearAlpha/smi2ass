"""Build and smoke-test standalone CLI and GUI executables."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

# Resolve sibling build tools even when invoked with Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_common import ROOT, executable_name, selected_targets, smoke_test

CLI_EXCLUSIONS = (
    "smi2ass.gui", "smi2ass.gui_launcher", "smi2ass.gui_preview",
    "smi2ass.gui_settings", "smi2ass.gui_smoke", "PySide6",
)


def build_target(target):
    """Compile one target, copy editable defaults beside it, and verify the result."""
    output = ROOT / "build" / target
    output.mkdir(parents=True, exist_ok=True)
    # Python 3.14 respects CPU affinity; older interpreters use the host CPU count.
    jobs = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    print(f"Compiling {target.upper()} with {jobs} parallel jobs.", flush=True)
    command = [
        sys.executable, "-m", "nuitka", "--standalone", "--onefile",
        "--assume-yes-for-downloads", "--remove-output", f"--jobs={jobs}",
        "--include-package=smi2ass", "--include-package-data=smi2ass",
        "--nofollow-import-to=smi2ass.test",
        f"--output-dir={output}", f"--output-filename={executable_name(target)}",
    ]
    if target == "gui":
        command += ["--enable-plugin=pyside6", "--include-qt-plugins=platforms"]
        if os.name == "nt":
            command.append("--windows-console-mode=disable")
        entry = "gui_standalone.py"
    else:
        # Keep optional Qt modules out of the standalone CLI, even if installed locally.
        command.append("--nofollow-import-to=" + ",".join(CLI_EXCLUSIONS))
        entry = "standalone.py"
    command.append(str(ROOT / "scripts" / entry))
    env = os.environ.copy()
    # Expose tools in the active venv without requiring shell activation.
    env["PATH"] = str(Path(sys.executable).absolute().parent) + os.pathsep + env.get("PATH", "")
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    # Editable sibling defaults take priority over embedded data in compiled programs.
    settings = output / "setting"
    if settings.exists():
        shutil.rmtree(settings)
    shutil.copytree(ROOT / "src" / "setting", settings)
    smoke_test(target, output / executable_name(target))


def main():
    # Build targets sequentially because each compiler already uses all available CPUs.
    for target in selected_targets():
        build_target(target)


if __name__ == "__main__":
    main()
