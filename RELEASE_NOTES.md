# V1.5.1

## Fixes and improvements

- Fix local distribution checks that could skip the wheel when inherited package metadata made it appear already installed. Force installation of the selected artifact and isolate Python, pip, and console checks from the calling environment.
- Show captured CLI stdout/stderr when smoke tests fail, so the underlying error is visible.
- Add `build.sh` for Linux x86-64 and `build.ps1` for Windows x86-64. Each script sets up `.build-venv`, builds and verifies wheel/source distributions, compiles the executable, and tests the ZIP/7z archives. CI runs these same scripts.
- Build packages and executables with Python 3.14 and pin Linux CI jobs to Ubuntu 26.04. Regression tests still cover Python 3.11–3.14 on Windows and Linux.
- List all seven release assets and provide SHA-256 verification commands for Windows PowerShell, Linux, and macOS.

## Compatibility

Python source/package installations require **Python 3.11 or later**. The local build scripts require **Python 3.14 x86-64** and a native C compiler. Standalone executables do not require Python; Windows and Linux archives target x86-64.

**Linux build baseline:** V1.5.1 binaries are built and tested on Ubuntu 26.04, replacing the Ubuntu 22.04 baseline used for V1.5. Compatibility with older Linux distributions has not been verified.

Default CLI output remains `./out`. Single-language output is `name.ass`; multilingual output is `name-ENG.ass`, `name-KOR.ass`, etc. For custom settings, use `--settings-dir PATH`. Executable archives retain an editable `setting` folder beside the executable.

## Downloads

Use the ZIP or 7z archive for your OS and extract the entire archive. Keep the `setting` directory beside the executable. Python users can install the attached wheel with `python -m pip install smi2ass-1.5.1-py3-none-any.whl`. Packages are attached to this GitHub release; no PyPI publication is implied.

`SHA256SUMS.txt` covers all six distributions. Executable archives include `BUILD-INFO.json` with the source commit, Python version, platform, and installed build/runtime dependencies.

### V1.5.1 assets and SHA-256 verification

The [V1.5.1 release](https://github.com/LinearAlpha/smi2ass/releases/tag/V1.5.1) has seven assets:

- `SHA256SUMS.txt` (checksums for the six distributions below)
- `smi2ass-1.5.1-py3-none-any.whl`
- `smi2ass-1.5.1.tar.gz`
- `smi2ass_linux_x86-64.7z`
- `smi2ass_linux_x86-64.zip`
- `smi2ass_windows_x86-64.7z`
- `smi2ass_windows_x86-64.zip`

Download `SHA256SUMS.txt` and your chosen distribution from that release into the same directory. Run the following there before extracting or installing, replacing the example filename with your downloaded asset's exact name.

**Windows PowerShell:**

```powershell
$file = 'smi2ass_windows_x86-64.zip'
$line = Get-Content .\SHA256SUMS.txt | Where-Object { $_.EndsWith("  $file") }
if (!$line) { throw "No checksum for $file" }
$expected = ($line -split '\s+')[0]
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash -ne $expected) {
    throw "SHA-256 verification failed: $file"
}
"Verified: $file"
```

**Linux:**

```sh
file='smi2ass_linux_x86-64.zip'
awk -v file="$file" '$2 == file { print }' SHA256SUMS.txt | sha256sum -c -
```

**macOS:**

```sh
file='smi2ass-1.5.1-py3-none-any.whl'
awk -v file="$file" '$2 == file { print }' SHA256SUMS.txt | shasum -a 256 -c -
```

Proceed only when PowerShell prints `Verified: <filename>` or Linux/macOS prints `<filename>: OK`. A mismatch, missing file, or missing checksum is a verification failure.

[Full changelog](https://github.com/LinearAlpha/smi2ass/compare/V1.5...V1.5.1)
