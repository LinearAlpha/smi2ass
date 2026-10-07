# smi2ass

`smi2ass` converts SAMI (`.smi`) subtitles to SSA/ASS (SubStation Alpha), including separate output files for multiple languages.

## Download or install

[Download V1.5.1](https://github.com/LinearAlpha/smi2ass/releases/tag/V1.5.1) for **Windows x86-64** or **Linux x86-64**. Extract the entire ZIP or 7z archive and keep the editable `setting` directory beside the executable. Standalone executables do not require Python. V1.5.1 Linux binaries are built and tested on Ubuntu 26.04.

The release includes `SHA256SUMS.txt` for verifying downloads. Each executable archive includes `BUILD-INFO.json` identifying the source commit and build dependencies.

For a Python installation, use **Python 3.11 or later** and install the wheel attached to the release:

```shell
python -m pip install smi2ass-1.5.1-py3-none-any.whl
```

Or install from a checkout:

```shell
python -m pip install .
```

Both installations provide the `smi2ass` command and `python -m smi2ass`. Runtime dependencies (`beautifulsoup4`, `charset-normalizer`, and `webcolors`) are installed automatically. The packages are distributed through GitHub Releases; these commands do not assume a PyPI release.

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

## Usage

```shell
smi2ass --version
smi2ass my_subtitles.smi
smi2ass -o converted "first episode.smi" "second episode.smi"
smi2ass --add_time 500 -f "Arial" -s 36 my_subtitles.smi
smi2ass --sub_time 500 my_subtitles.smi
smi2ass --help
```

For an extracted executable, use `./smi2ass` on Linux or `.\smi2ass.exe` in Windows PowerShell. On Linux, if necessary, run `chmod +x smi2ass` after extraction.

By default, files are written to `out` under the current working directory. A single-language subtitle produces `out/my_subtitles.ass`. A multilingual subtitle produces files such as:

```text
out/my_subtitles-ENG.ass
out/my_subtitles-KOR.ass
```

Use `-o` to select another output directory. Time offsets are in milliseconds; use either `--add_time` or `--sub_time`.

### Settings

Default font styles and language codes are bundled with the Python package, so conversion works from any directory. Executables use the editable `setting/ass_styles.json` and `setting/lan_code.json` files beside the executable when that folder exists.

For custom settings with any installation, copy the defaults from [`src/setting`](src/setting) into your own directory, edit them, and run:

```shell
smi2ass --settings-dir my-settings my_subtitles.smi
```

**Upgrading:** source defaults now live in `src/setting`; source/package installations no longer implicitly read `./setting`. Use `--settings-dir` for an existing custom directory. Python 3.11 is the supported minimum, correcting the older metadata's unsupported `>3.7` claim.

### Supported tags and input encodings

The converter handles paragraph, line-break, bold, italic, underline, strike-through, and font-color tags. Input encoding is detected by charset-normalizer; regression tests cover Korean CP949/EUC-KR and UTF-8, UTF-8 BOM, and UTF-16 inputs. Output is UTF-8 ASS. Automatic encoding detection is heuristic; check the output when working with unusual or very short inputs.

### Fixing a bad SAMI file

The converter prints the file being processed and diagnostic fragments for malformed language or time tags. For example, a misspelled `Start` attribute can produce `Failed to extract time code`. Correct the `.smi` file and run the conversion again.

## Development and testing

Create and activate a virtual environment, then install the project:

```shell
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s src/test -v
python scripts/smoke_test.py
```

CI runs the regression tests and installed CLI smoke tests on **Python 3.11–3.14, Windows and Ubuntu 26.04**. It also builds and tests wheel/source installations in fresh environments, compiles Linux/Windows executables with Python 3.14 (Linux builds use Ubuntu 26.04), and tests both extracted archive formats outside the checkout.

## Build distributions

For a complete local build, install **Python 3.14 x86-64** and a native C compiler (GCC on Linux or a supported Windows compiler), then run the script for your OS from the checkout:

```shell
# Linux x86-64
./build.sh
```

```powershell
# Windows x86-64
.\build.ps1
```

The scripts create or reuse `.build-venv`, install build/runtime dependencies, build and check the wheel/source distributions, and compile, archive, and smoke-test the executable for your OS. No virtual-environment activation is needed. Each script stops on a failed step. Old `smi2ass` wheel/source files in `dist` are replaced so repeated builds verify only the current pair.

To run the same steps manually with a Python 3.14 virtual environment active:

```shell
python -m pip install . -r requirements-build.txt
python -m build
python -m twine check --strict dist/*
python scripts/check_distributions.py
python scripts/build_executable.py
python scripts/package_assets.py
```

Wheel/source distributions are written to `dist`; executable ZIP/7z archives are written to `release-assets`. Nuitka requires a native C compiler (GCC on Linux or a supported Windows compiler); Linux additionally uses `patchelf`. `scripts/build_executable.py` uses the active Python environment and is the authoritative standalone/one-file build configuration.

To prepare a release, update the project and CLI versions together, update `RELEASE_NOTES.md` and `CHANGELOG.md`, and merge a commit titled `release: V<version>` into `main`. The CI workflow publishes only after all test, package, and executable jobs succeed. It creates a draft, uploads the six distributions plus SHA-256 checksums, then publishes. Ordinary commits and PRs only validate artifacts. An existing release is never overwritten. Maintainers may also run CI manually on `main` with `publish` enabled.

See [release notes](RELEASE_NOTES.md) and [the changelog](CHANGELOG.md).

## Contributors and origins

This project builds on [@hojel's service.subtitles.gomtv](https://github.com/hojel/service.subtitles.gomtv/tree/3a7342961e140eaf8250659b0ac6158ce5e6bc5c/resources/lib) and [@trustin's smi2ass](https://github.com/trustin/smi2ass/tree/v0.1.1), which provided the original conversion script.

| Contributor | Contributions |
| --- | --- |
| [@LinearAlpha](https://github.com/LinearAlpha) (Minpyo Kim) | Maintains this project; rewrote the converter using classes; corrected RGB-to-BGR handling; added JSON-based ASS settings, CLI font/title/resolution controls, time offsets, builds, and color regression tests/CI ([#2](https://github.com/LinearAlpha/smi2ass/pull/2)). |
| [@najoan125](https://github.com/najoan125) (Najoan) | Fixed named font colors by removing the leading `#` before RGB-to-BGR conversion ([#1](https://github.com/LinearAlpha/smi2ass/pull/1)); replaced chardet with charset-normalizer and reported the related executable-build problem ([#3](https://github.com/LinearAlpha/smi2ass/pull/3)). |
| [@hojel](https://github.com/hojel) and [@trustin](https://github.com/trustin) | Original upstream subtitle conversion work from which this project was forked. |

Thanks to everyone who contributes code, tests, bug reports, and improvements. See the [commit history](https://github.com/LinearAlpha/smi2ass/commits/main/) for individual changes. Licensing terms are in [LICENSE.txt](LICENSE.txt).
