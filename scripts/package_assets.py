"""Archive each tested executable with editable settings and build provenance."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

import py7zr

# Resolve sibling build tools even when invoked with Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_common import ROOT, archive_name, executable_name, project_version, selected_targets, smoke_test


def build_info(target):
    """Record target, commit, runtime, and dependencies for build reports.

    Args:
        target (str): Program whose build provenance is being recorded.

    Returns:
        dict: Version, target, commit, Python, platform, and dependency metadata.

    Raises:
        subprocess.CalledProcessError: Git or dependency metadata collection fails.
        OSError: Project metadata or required commands cannot be accessed.
    """
    return {
        "version": project_version(), "target": target,
        "commit": os.environ.get("GITHUB_SHA") or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "packages": subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines(),
    }


def package_target(target):
    """Create separate ZIP/7z archives and verify both extracted copies.

    Args:
        target (str): Built CLI or GUI program to archive.

    Raises:
        OSError: Required build outputs cannot be copied or archives cannot be written.
        subprocess.CalledProcessError: An extracted executable fails its smoke test.
    """
    output = ROOT / "release-assets"
    output.mkdir(exist_ok=True)
    name = archive_name(target)
    executable = executable_name(target)
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory) / name
        stage.mkdir()
        # Each download contains exactly its corresponding program, with shared defaults.
        shutil.copy2(ROOT / "build" / target / executable, stage / executable)
        shutil.copytree(ROOT / "build" / target / "setting", stage / "setting")
        for filename in ("README.md", "LICENSE.txt", "CHANGELOG.md"):
            shutil.copy2(ROOT / filename, stage / filename)
        (stage / "BUILD-INFO.json").write_text(json.dumps(build_info(target), indent=2)+"\n", encoding="utf-8")
        zip_path = shutil.make_archive(str(output / name), "zip", stage)
        seven_zip_path = output / f"{name}.7z"
        with py7zr.SevenZipFile(seven_zip_path, "w") as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        # Exercise each actual archive after extraction, outside the checkout.
        for extension in ("zip", "7z"):
            extracted = Path(directory) / extension
            extracted.mkdir()
            if extension == "zip":
                shutil.unpack_archive(zip_path, extracted)
            else:
                with py7zr.SevenZipFile(seven_zip_path) as archive:
                    archive.extractall(extracted)
            binary = extracted / executable
            # ZIP extraction can lose Unix execute bits; restore them before launching the copy.
            binary.chmod(binary.stat().st_mode | 0o111)
            smoke_test(target, binary)
    print(f"Created and verified {name}.zip and {name}.7z")


def main():
    """Package and verify each target selected by command-line options."""
    for target in selected_targets():
        package_target(target)


if __name__ == "__main__":
    main()
