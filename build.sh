#!/usr/bin/env bash
# Build and verify the Python distributions and Linux executable archives.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    echo "build.sh requires Linux x86-64. On Windows, use build.ps1." >&2
    exit 1
fi

unset PYTHONHOME PYTHONPATH
version_check='import platform, sys; sys.exit(0 if sys.version_info[:2] == (3, 14) and sys.maxsize > 2**32 and platform.machine().lower() in ("amd64", "x86_64") else 1)'
bootstrap_python=''
for candidate in python3.14 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -I -c "$version_check"; then
        bootstrap_python="$candidate"
        break
    fi
done
if [[ -z "$bootstrap_python" ]]; then
    echo "Install Python 3.14 x86-64 and make it available on PATH, then rerun build.sh." >&2
    exit 1
fi

build_python="$PWD/.build-venv/bin/python"
if [[ -e .build-venv ]]; then
    if [[ ! -x "$build_python" ]] || ! "$build_python" -I -c "$version_check"; then
        echo "The existing .build-venv is not a Python 3.14 x86-64 environment. Rename or remove it and rerun build.sh." >&2
        exit 1
    fi
else
    "$bootstrap_python" -I -m venv .build-venv
fi

"$build_python" -I -m pip --isolated install -r requirements-build.txt
"$build_python" -I -m pip --isolated install --force-reinstall .
"$build_python" -I -m pip --isolated check
# Remove only this project's old Python artifacts before building the new pair.
rm -f -- dist/smi2ass-*.whl dist/smi2ass-*.tar.gz
"$build_python" -I -m build
"$build_python" -I -m twine check --strict dist/*.whl dist/*.tar.gz
"$build_python" -I scripts/check_distributions.py
"$build_python" -I scripts/build_executable.py
"$build_python" -I scripts/package_assets.py

echo "Build complete: wheel/source distributions in dist; executable ZIP/7z archives in release-assets."
