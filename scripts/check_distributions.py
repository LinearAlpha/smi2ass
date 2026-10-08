"""Install each distribution in an isolated environment and test its CLI."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def check_distribution(artifact, gui=False):
    """Install the exact artifact and verify its declared entry points.

    Args:
        artifact (Path): Exact wheel or source archive to install.
        gui (bool): Whether to install the GUI extra and run desktop checks. Defaults to
            False.

    Raises:
        subprocess.CalledProcessError: Installation, dependency checks, or smoke tests
            fail.
        OSError: The temporary environment cannot be created or launched.
    """
    # Do not expose the calling checkout or another Python installation to the
    # temporary interpreter or the generated console entry point.
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
    with tempfile.TemporaryDirectory() as directory:
        environment = Path(directory) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        bindir = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = bindir / ("python.exe" if sys.platform == "win32" else "python")
        console = bindir / ("smi2ass.exe" if sys.platform == "win32" else "smi2ass")
        python_command = [str(python), "-I"]
        # Force the artifact to install even if inherited metadata advertises the same version.
        # pip --isolated also ignores user configuration such as an unrelated PIP_TARGET.
        subprocess.run(python_command + ["-m", "pip", "--isolated", "install",
                                        "--force-reinstall", str(artifact) + ("[gui]" if gui else "")],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + ["-m", "pip", "--isolated", "check"],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + [str(ROOT / "scripts" / "smoke_test.py")],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + [str(ROOT / "scripts" / "smoke_test.py"),
                                        "--executable", str(console)],
                       check=True, cwd=directory, env=env)
        # Installing the extra exercises Qt and packaged resources from the artifact itself.
        if gui:
            subprocess.run(python_command + [str(ROOT / "scripts" / "smoke_gui.py")],
                           check=True, cwd=directory, env=env)
    print(f"Verified {artifact.name}")


def main():
    """Verify the wheel and source distribution currently present in dist.

    Raises:
        RuntimeError: The distribution count is not exactly two.
        subprocess.CalledProcessError: A distribution fails installation or
            verification.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Also install and exercise the optional desktop GUI")
    args = parser.parse_args()
    artifacts = sorted((ROOT / "dist").glob("*.whl")) + sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(artifacts) != 2:
        raise RuntimeError(f"Expected one wheel and one sdist, got {artifacts}")
    for artifact in artifacts:
        check_distribution(artifact, gui=args.gui)


if __name__ == "__main__":
    main()

