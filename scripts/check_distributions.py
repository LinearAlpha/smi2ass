"""Install each distribution in an isolated environment and test its CLI."""
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    artifacts = sorted((ROOT / "dist").glob("*.whl")) + sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(artifacts) != 2:
        raise RuntimeError(f"Expected one wheel and one sdist, got {artifacts}")
    for artifact in artifacts:
        with tempfile.TemporaryDirectory() as directory:
            environment = Path(directory) / "venv"
            venv.EnvBuilder(with_pip=True).create(environment)
            bindir = environment / ("Scripts" if sys.platform == "win32" else "bin")
            python = bindir / ("python.exe" if sys.platform == "win32" else "python")
            console = bindir / ("smi2ass.exe" if sys.platform == "win32" else "smi2ass")
            subprocess.run([str(python), "-m", "pip", "install", str(artifact)], check=True, cwd=directory)
            subprocess.run([str(python), "-m", "pip", "check"], check=True, cwd=directory)
            subprocess.run([str(python), str(ROOT / "scripts" / "smoke_test.py")], check=True, cwd=directory)
            subprocess.run([str(python), str(ROOT / "scripts" / "smoke_test.py"), "--executable", str(console)], check=True, cwd=directory)
        print(f"Verified {artifact.name}")


if __name__ == "__main__":
    main()
