"""Build and smoke-test a standalone executable using the active environment."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = os.environ.copy()
    # build.sh/build.ps1 invoke the venv interpreter without activating it.
    # Make tools installed into that environment (including patchelf) visible.
    env["PATH"] = str(Path(sys.executable).absolute().parent) + os.pathsep + env.get("PATH", "")
    output = ROOT / "build"
    output.mkdir(exist_ok=True)
    name = "smi2ass.exe" if os.name == "nt" else "smi2ass"
    subprocess.run([
        sys.executable, "-m", "nuitka", "--standalone", "--onefile",
        "--assume-yes-for-downloads", "--remove-output", "--jobs=2",
        "--include-package=smi2ass", "--include-package-data=smi2ass",
        "--nofollow-import-to=smi2ass.test",
        "--nofollow-import-to=smi2ass.gui,smi2ass.gui_launcher,smi2ass.gui_preview,smi2ass.gui_settings,smi2ass.gui_smoke,PySide6",
        f"--output-dir={output}", f"--output-filename={name}",
        str(ROOT / "scripts" / "standalone.py"),
    ], check=True, cwd=ROOT, env=env)
    settings = output / "setting"
    if settings.exists():
        shutil.rmtree(settings)
    shutil.copytree(ROOT / "src" / "setting", settings)
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "smoke_test.py"),
        "--executable", str(output / name),
    ], check=True)

    gui_name = "smi2ass-gui.exe" if os.name == "nt" else "smi2ass-gui"
    gui_options = ["--windows-console-mode=disable"] if os.name == "nt" else []
    subprocess.run([
        sys.executable, "-m", "nuitka", "--standalone", "--onefile",
        "--assume-yes-for-downloads", "--remove-output", "--jobs=2",
        "--enable-plugin=pyside6", "--include-qt-plugins=platforms",
        "--include-package=smi2ass", "--include-package-data=smi2ass",
        "--nofollow-import-to=smi2ass.test",
        f"--output-dir={output}", f"--output-filename={gui_name}",
        *gui_options, str(ROOT / "scripts" / "gui_standalone.py"),
    ], check=True, cwd=ROOT, env=env)
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "smoke_gui.py"),
        "--executable", str(output / gui_name),
    ], check=True)


if __name__ == "__main__":
    main()

