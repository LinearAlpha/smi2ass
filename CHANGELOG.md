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

## Contributors

Thanks to @LinearAlpha for maintenance, the class-based converter, configurable ASS styling, CLI/time offsets, and regression CI; @najoan125 for the color fix and charset-normalizer migration; and the original upstream projects by @hojel and @trustin.

[Full changelog](https://github.com/LinearAlpha/smi2ass/compare/V1.4.5...V1.5)
