"""Exercise an installed CLI or extracted executable outside the checkout."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

KOREAN = "안녕하세요. 오늘은 날씨가 맑습니다. 자막 변환을 확인합니다. 함께 영화를 감상해요."


def sample(text: str, language: str = "ENCC") -> str:
    return f'''<SAMI><BODY>
<SYNC Start=1000><P Class={language}><FONT COLOR=red>{text}</FONT>
<SYNC Start=2000><P Class={language}>&nbsp;
</BODY></SAMI>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable")
    args = parser.parse_args()
    command = [str(Path(args.executable).resolve())] if args.executable else [sys.executable, "-m", "smi2ass"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)

        def run(*arguments):
            return subprocess.run(command + list(arguments), cwd=root, check=True,
                                  text=True, encoding="utf-8", capture_output=True)

        assert run("--version").stdout.strip() == "smi2ass 1.5"
        assert "--settings-dir" in run("--help").stdout
        english = root / "English sample.smi"
        english.write_text(sample("Red text"), encoding="utf-8-sig")
        korean = root / "Korean sample.smi"
        korean.write_bytes(sample(KOREAN, "KRCC").encode("cp949"))
        run("-f", "Test Font", "-s", "36", "--add_time", "500", str(english), str(korean))
        text = (root / "out" / "English sample.ass").read_text(encoding="utf-8")
        assert r"{\c&H0000ff&}Red text{\c}" in text
        assert "0:00:01.50,0:00:02.50" in text
        assert "Test Font,36" in text
        text = (root / "out" / "Korean sample.ass").read_text(encoding="utf-8")
        assert KOREAN in text and "Red text" not in text and "\ufffd" not in text
        bilingual = root / "bilingual.smi"
        bilingual.write_text('''<SAMI><BODY>
<SYNC Start=1000><P Class=ENCC>Hello
<SYNC Start=1000><P Class=KRCC>안녕하세요
<SYNC Start=2000><P Class=ENCC>&nbsp;
<SYNC Start=2000><P Class=KRCC>&nbsp;
</BODY></SAMI>''', encoding="utf-8-sig")
        run("-o", "translated", "--sub_time", "500", str(bilingual))
        files = sorted(p.name for p in (root / "translated").glob("*.ass"))
        assert files == ["bilingual-ENG.ass", "bilingual-KOR.ass"], files
        for path in (root / "translated").glob("*.ass"):
            assert "0:00:00.50,0:00:01.50" in path.read_text(encoding="utf-8")
        # Reusing one converter across files must not carry languages forward.
        run("-o", "batch", str(bilingual), str(english))
        assert (root / "batch" / "English sample.ass").is_file()
        assert not (root / "batch" / "English sample-KOR.ass").exists()
    print("CLI smoke tests passed (version, settings, encodings, colors, offsets, batch, multilingual output).")


if __name__ == "__main__":
    main()
