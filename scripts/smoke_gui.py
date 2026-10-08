"""Run the installed/compiled GUI offscreen, outside the source checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable")
    args = parser.parse_args()
    command = [str(Path(args.executable).resolve())] if args.executable else [sys.executable,"-I","-m","smi2ass.gui_launcher"]
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.pop("PYTHONPATH",None)
    env.pop("PYTHONHOME",None)
    with tempfile.TemporaryDirectory() as directory:
        report = Path(directory) / "report.json"
        result = subprocess.run(command+["--smoke-test",str(report)],cwd=directory,env=env,
                                capture_output=True,text=True,encoding="utf-8",timeout=90)
        if result.returncode or not report.exists():
            print(result.stdout,file=sys.stderr)
            print(result.stderr,file=sys.stderr)
            if report.exists():
                print(report.read_text(encoding="utf-8"),file=sys.stderr)
            raise RuntimeError(f"GUI smoke test failed with exit status {result.returncode}")
        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["ok"],data
        print("GUI smoke tests passed: " + ", ".join(data["checks"]))


if __name__ == "__main__":
    main()
