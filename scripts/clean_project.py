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
    """Detect symlinks and Windows junctions when the API is available.

    Args:
        path (Path): Candidate filesystem entry.

    Returns:
        bool: Whether the entry is a symlink or supported Windows junction.
    """
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def remove_generated(path):
    """Remove an output or its link without traversing a linked destination.

    Args:
        path (Path): Known generated output or link to remove.

    Returns:
        bool: True if an entry was removed; False if it was already absent.

    Raises:
        OSError: The entry cannot be removed.
    """
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
    """Clean generated entries and return their relative project paths.

    Args:
        root (Path | str): Project root to clean. Defaults to this checkout.

    Returns:
        list[str]: Removed entries as paths relative to the project root.

    Raises:
        OSError: A generated output cannot be removed.
    """
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
    """Clean known generated outputs and print the removed project paths.

    Raises:
        OSError: Cleanup cannot remove a generated output.
    """
    argparse.ArgumentParser(description=__doc__).parse_args()
    removed = clean_project()
    for name in removed:
        print(f"Removed {name}")
    print("Project cleanup complete." if removed else "Project is already clean.")


if __name__ == "__main__":
    main()
