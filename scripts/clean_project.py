"""Remove generated project outputs and Python caches, preserving source and venvs."""
import argparse
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
# Clean only known project outputs; never infer deletions from arbitrary untracked files.
GENERATED = (
    "build", "dist", "release-assets", "smi2ass.egg-info", "src/smi2ass.egg-info",
    "__pycache__", ".pytest_cache", "nuitka-crash-report.xml",
)
VIRTUAL_ENVS = {".venv", "venv", ".build-venv", ".wheel-venv", ".sdist-venv"}


def is_link(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def remove_generated(path):
    """Remove an output or its link without traversing a linked destination."""
    if path.is_symlink():
        path.unlink()
    elif getattr(path, "is_junction", lambda: False)():
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    else:
        return False
    return True


def clean_project(root=ROOT):
    """Return removed paths relative to the project root; repeated cleanup is harmless."""
    root = Path(root).resolve()
    removed = []
    for name in GENERATED:
        path = root / name
        # A redirected source folder is outside the cleanup scope.
        if name.startswith("src/") and is_link(root / "src"):
            continue
        if remove_generated(path):
            removed.append(path.relative_to(root).as_posix())
    for name in ("src", "scripts"):
        folder = root / name
        if is_link(folder):
            continue
        # Prune linked folders and virtual environments before descending into caches.
        for current, directories, _ in os.walk(folder, followlinks=False):
            for directory in list(directories):
                path = Path(current) / directory
                if directory == "__pycache__":
                    if remove_generated(path):
                        removed.append(path.relative_to(root).as_posix())
                    directories.remove(directory)
                elif directory in VIRTUAL_ENVS or is_link(path) or (path / "pyvenv.cfg").is_file():
                    directories.remove(directory)
    return removed


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    removed = clean_project()
    for name in removed:
        print(f"Removed {name}")
    print("Project cleanup complete." if removed else "Project is already clean.")


if __name__ == "__main__":
    main()
