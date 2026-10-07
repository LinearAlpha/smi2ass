"""Install each distribution in an isolated environment and test its CLI."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def check_distribution(artifact):
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
        subprocess.run(python_command + ["-m", "pip", "--isolated", "install",
                                        "--force-reinstall", str(artifact)],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + ["-m", "pip", "--isolated", "check"],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + [str(ROOT / "scripts" / "smoke_test.py")],
                       check=True, cwd=directory, env=env)
        subprocess.run(python_command + [str(ROOT / "scripts" / "smoke_test.py"),
                                        "--executable", str(console)],
                       check=True, cwd=directory, env=env)
    print(f"Verified {artifact.name}")


def main():
    artifacts = sorted((ROOT / "dist").glob("*.whl")) + sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(artifacts) != 2:
        raise RuntimeError(f"Expected one wheel and one sdist, got {artifacts}")
    for artifact in artifacts:
        check_distribution(artifact)


if __name__ == "__main__":
    main()
