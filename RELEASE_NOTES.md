# V2

V2 (package version **2.0**) adds a desktop interface to the SAMI-to-ASS converter while keeping the existing CLI commands available.

## Desktop interface

- **Convert:** add files, drag and drop SAMI subtitles, or scan folders; select inputs, choose an output folder/preset, and adjust timing in milliseconds. Background batch conversion includes progress, cancellation between files, and per-file error details.
- **ASS Settings:** edit fonts, emphasis, four colors and opacity, outline/shadow, alignment, margins, and canvas size. Advanced options cover scaling, spacing, rotation, encoding, script title, timer, and collision handling.
- Preview style changes immediately, save named presets, and import/export settings compatible with the CLI's JSON format. The preview is illustrative; final rendering depends on the player's ASS renderer and installed fonts.
- Choose persistent **Light** or **Dark** themes. Confirm replacement of existing output files; conflicting output names are blocked.
- Launch the desktop program as `smi2ass-gui`. Windows GUI executables open without a console.

[Program screenshots](https://github.com/LinearAlpha/smi2ass#screenshots)

## Conversion, builds, and maintenance

- Expand language mapping to 184 languages and 843 class aliases, including ISO code variants and selected regional SAMI classes. Preserve existing output codes and unknown fallback; fix case-insensitive `EnglishSC` recognition.
- Write the selected ASS style name into Dialogue events, preserve zero-start cues, and round timing correctly across second boundaries. Report unusable inputs and support Unicode paths in legacy Windows consoles.
- Build separate CLI/GUI executables and archives with `build.sh` and `build.ps1`; both targets are built by default. Add clean-before-build and cleanup-only modes, and use all available logical CPUs during compilation.
- Verify installed distributions, GUI behavior, native executables, and both extracted archive formats in CI. Include real screenshots with the README in source/native archives.
- Add consistent Google-style docstrings to all functions and classes for easier maintenance.

## Compatibility and installation

Standalone Windows/Linux **x86-64** executables do not require Python. Extract the entire ZIP or 7z archive and keep the editable `setting` directory beside its executable. Linux binaries are built and tested on **Ubuntu 26.04**; compatibility with older Linux distributions has not been verified. Linux GUI usage requires a desktop session and the Qt runtime libraries listed in the README.

Python installations require **Python 3.11 or later**. The GUI extra is optional; the CLI keeps its existing commands, settings format, timing flags, and default `./out` folder. Python GUI installations also work on macOS. Local native builds use **Python 3.14 x86-64** and a C compiler.

Install the downloaded wheel for the CLI:

```shell
python -m pip install smi2ass-2.0-py3-none-any.whl
smi2ass --version
```

Or install the GUI extra:

```shell
python -m pip install "./smi2ass-2.0-py3-none-any.whl[gui]"
smi2ass-gui
```

These packages are attached to GitHub Releases; no PyPI publication is implied.

## Assets and SHA-256 verification

The prepared V2 release contains eleven assets:

- `SHA256SUMS.txt` (checksums for the ten distributions below)
- `smi2ass-2.0-py3-none-any.whl`
- `smi2ass-2.0.tar.gz`
- `smi2ass_linux_x86-64.7z`
- `smi2ass_linux_x86-64.zip`
- `smi2ass_windows_x86-64.7z`
- `smi2ass_windows_x86-64.zip`
- `smi2ass-gui_linux_x86-64.7z`
- `smi2ass-gui_linux_x86-64.zip`
- `smi2ass-gui_windows_x86-64.7z`
- `smi2ass-gui_windows_x86-64.zip`

Choose the `smi2ass-gui` archive for the desktop program or `smi2ass` for the CLI. Every native archive includes editable settings and `BUILD-INFO.json` identifying its target, source commit, Python version, and dependencies.

Download `SHA256SUMS.txt` and your chosen distribution into the same directory. Verify it there before extracting/installing, replacing the example filename with your asset's exact name.

**Windows PowerShell:**

```powershell
$file = 'smi2ass-gui_windows_x86-64.zip'
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
file='smi2ass-gui_linux_x86-64.zip'
awk -v file="$file" '$2 == file { print }' SHA256SUMS.txt | sha256sum -c -
```

**macOS (wheel):**

```sh
file='smi2ass-2.0-py3-none-any.whl'
awk -v file="$file" '$2 == file { print }' SHA256SUMS.txt | shasum -a 256 -c -
```

Proceed when PowerShell prints `Verified: <filename>` or Linux/macOS prints `<filename>: OK`. A mismatch, missing file, or missing checksum is a verification failure.

[Full changelog](https://github.com/LinearAlpha/smi2ass/compare/V1.5.1...V2)
