# Unreleased

- Add a native desktop GUI with Convert and ASS Settings tabs, drag-and-drop/folder input, background batch conversion, timing offsets, progress, cancellation, and per-file errors.
- Add a live illustrative style preview, editable ASS settings, persistent presets, and compatible JSON import/export. Require confirmation before replacing existing output files and detect duplicate output names.
- Keep Qt optional for Python CLI installations; add the `smi2ass-gui` launcher and build a companion GUI executable in each Windows/Linux archive. Test the GUI on Python 3.14 and in both extracted archive formats.
- Write the selected ASS style name into dialogue events and report a useful error for files with no usable subtitle cues.

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

# V1.5

## Fixes and improvements

- Fix named font colors in ASS output; thanks to @najoan125 ([#1](https://github.com/LinearAlpha/smi2ass/pull/1)).
- Replace chardet with charset-normalizer; thanks to @najoan125 ([#3](https://github.com/LinearAlpha/smi2ass/pull/3)). Regression tests cover Korean CP949/EUC-KR and Unicode inputs.
- Fix saving multilingual subtitles as separate sibling files, and clear previous-language output when processing multiple input files.
- Provide installable wheel/source distributions with complete runtime dependencies, a working `smi2ass` command, bundled default settings, and corrected license metadata.
- Add `--version` and `--settings-dir`; settings no longer depend on the current working directory. Executable archives retain an editable `setting` folder.
- Expand CI to Python 3.11–3.14 on Windows and Linux, clean wheel/source installs, and compiled executable/archive smoke tests.
- Document installation, actual output names, builds, and project contributions.

## Compatibility

Python source/package installations require **Python 3.11 or later**, matching the existing use of `typing.Self`. Standalone executables do not require Python. Linux x86-64 binaries are built on Ubuntu 22.04 (glibc 2.35); Windows binaries target x86-64. Other executable platforms are not included in this release.

Default CLI output is `./out`. Single-language output is `name.ass`; multilingual output is `name-ENG.ass`, `name-KOR.ass`, etc. For custom settings in source/package installations, pass `--settings-dir PATH`; repository defaults now live in `src/setting`.

## Downloads

Use the ZIP or 7z archive for your OS and extract the entire archive. Keep the `setting` directory beside the executable. Python users can install the attached wheel with `python -m pip install smi2ass-1.5-py3-none-any.whl`. Packages are attached to this GitHub release; no PyPI publication is implied.

`SHA256SUMS.txt` covers every downloadable distribution. Executable archives include `BUILD-INFO.json` with the source commit, Python version, platform, and installed build/runtime dependencies.

### V1.5 assets and SHA-256 verification

The [V1.5 release](https://github.com/LinearAlpha/smi2ass/releases/tag/V1.5) has seven assets:

- `SHA256SUMS.txt` (checksums for the six distributions below)
- `smi2ass-1.5-py3-none-any.whl`
- `smi2ass-1.5.tar.gz`
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
file='smi2ass-1.5-py3-none-any.whl'
awk -v file="$file" '$2 == file { print }' SHA256SUMS.txt | shasum -a 256 -c -
```

Proceed only when PowerShell prints `Verified: <filename>` or Linux/macOS prints `<filename>: OK`. A mismatch, missing file, or missing checksum is a verification failure.

## Contributors

Thanks to @LinearAlpha for maintenance, the class-based converter, configurable ASS styling, CLI/time offsets, and regression CI; @najoan125 for the color fix and charset-normalizer migration; and the original upstream projects by @hojel and @trustin.

[Full changelog](https://github.com/LinearAlpha/smi2ass/compare/V1.4.5...V1.5)

