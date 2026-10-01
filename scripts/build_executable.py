"""Build and smoke-test a standalone executable using the active environment."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / "build"
    output.mkdir(exist_ok=True)
    name = "smi2ass.exe" if os.name == "nt" else "smi2ass"
    subprocess.run([
        sys.executable, "-m", "nuitka", "--standalone", "--onefile",
        "--assume-yes-for-downloads", "--remove-output", "--jobs=2",
        "--include-package=smi2ass", "--include-package-data=smi2ass",
        "--nofollow-import-to=smi2ass.test",
        f"--output-dir={output}", f"--output-filename={name}",
        str(ROOT / "scripts" / "standalone.py"),
    ], check=True, cwd=ROOT)
    settings = output / "setting"
    if settings.exists():
        shutil.rmtree(settings)
    shutil.copytree(ROOT / "src" / "setting", settings)
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "smoke_test.py"),
        "--executable", str(output / name),
    ], check=True)


if __name__ == "__main__":
    main()
