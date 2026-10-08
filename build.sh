#!/usr/bin/env bash
# Build and verify Python distributions and selected Linux executables.
set -euo pipefail

target=all
if [[ $# -eq 2 && "$1" == --target ]]; then
    target="$2"
elif [[ $# -ne 0 ]]; then
    echo "Usage: ./build.sh [--target cli|gui|all]" >&2
    exit 2
fi
case "$target" in cli|gui|all) ;; *) echo "Unknown build target: $target" >&2; exit 2 ;; esac

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
project='.'
if [[ "$target" != cli ]]; then
    project='.[gui]'
fi
"$build_python" -I -m pip --isolated install --force-reinstall "$project"
"$build_python" -I -m pip --isolated check
# Remove only this project's old Python artifacts before building the new pair.
rm -f -- dist/smi2ass-*.whl dist/smi2ass-*.tar.gz
"$build_python" -I -m build
"$build_python" -I -m twine check --strict dist/*.whl dist/*.tar.gz
distribution_options=()
if [[ "$target" != cli ]]; then
    distribution_options+=(--gui)
fi
"$build_python" -I scripts/check_distributions.py "${distribution_options[@]}"
"$build_python" -I scripts/build_executable.py --target "$target"
"$build_python" -I scripts/package_assets.py --target "$target"

echo "Build complete ($target): wheel/source distributions in dist; executable ZIP/7z archives in release-assets."

