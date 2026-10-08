"""Archive tested executables with editable settings and build provenance."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

import py7zr

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "release-assets"
    output.mkdir(exist_ok=True)
    label = "windows" if os.name == "nt" else "linux"
    name = f"smi2ass_{label}_x86-64"
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory) / name
        stage.mkdir()
        executable = "smi2ass.exe" if os.name == "nt" else "smi2ass"
        shutil.copy2(ROOT / "build" / executable, stage / executable)
        gui_executable = "smi2ass-gui.exe" if os.name == "nt" else "smi2ass-gui"
        shutil.copy2(ROOT / "build" / gui_executable, stage / gui_executable)
        shutil.copytree(ROOT / "build" / "setting", stage / "setting")
        for filename in ("README.md", "LICENSE.txt", "CHANGELOG.md"):
            shutil.copy2(ROOT / filename, stage / filename)
        info = {
            "version": "1.5.1", "commit": os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "python": sys.version, "platform": platform.platform(),
            "packages": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines(),
        }
        (stage / "BUILD-INFO.json").write_text(json.dumps(info, indent=2)+"\n", encoding="utf-8")
        zip_path = shutil.make_archive(str(output / name), "zip", stage)
        with py7zr.SevenZipFile(output / f"{name}.7z", "w") as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        # Test the actual archives after extraction, not only the build directory.
        for extension in ("zip", "7z"):
            extracted = Path(directory) / extension
            extracted.mkdir()
            if extension == "zip":
                shutil.unpack_archive(zip_path, extracted)
            else:
                with py7zr.SevenZipFile(output / f"{name}.7z") as archive:
                    archive.extractall(extracted)
            binary = extracted / executable
            binary.chmod(binary.stat().st_mode | 0o111)
            subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke_test.py"), "--executable", str(binary)], check=True)
            gui_binary = extracted / gui_executable
            gui_binary.chmod(gui_binary.stat().st_mode | 0o111)
            subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke_gui.py"), "--executable", str(gui_binary)], check=True)
    print(f"Created and verified {name}.zip and {name}.7z")


if __name__ == "__main__":
    main()

