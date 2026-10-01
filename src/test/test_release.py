import contextlib
from importlib.metadata import version
from pathlib import Path
import tempfile
import unittest

from smi2ass import AssStyle, __version__, smi2ass

KOREAN = "안녕하세요. 오늘은 날씨가 맑습니다. 자막 변환을 확인합니다. 함께 영화를 감상해요."


def sample(text, language="ENCC"):
    return f'''<SAMI><BODY>
<SYNC Start=1000><P Class={language}><FONT COLOR=red>{text}</FONT>
<SYNC Start=2000><P Class={language}>&nbsp;
</BODY></SAMI>'''


class ReleaseRegressionTest(unittest.TestCase):
    def test_installed_version_matches_cli_version(self):
        self.assertEqual("1.5", __version__)
        self.assertEqual(__version__, version("smi2ass"))

    def test_default_settings_are_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with contextlib.chdir(directory):
                self.assertEqual("kor", AssStyle().get_lang_code("KRCC"))

    def test_legacy_and_unicode_encodings_preserve_text_in_saved_output(self):
        for encoding in ("cp949", "euc_kr", "utf-8", "utf-8-sig", "utf-16"):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / "sample.smi"
                path.write_bytes(sample(KOREAN, "KRCC").encode(encoding))
                smi2ass(str(path)).to_ass().save(root / "output")
                output = (root / "output" / "sample.ass").read_text(encoding="utf-8")
                self.assertIn(KOREAN, output)
                self.assertNotIn("\ufffd", output)
                self.assertIn(r"{\c&H0000ff&}", output)

    def test_multiple_languages_save_as_sibling_files_and_reset_between_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bilingual.smi"
            path.write_text('''<SAMI><BODY>
<SYNC Start=1000><P Class=ENCC>Hello
<SYNC Start=1000><P Class=KRCC>안녕하세요
<SYNC Start=2000><P Class=ENCC>&nbsp;
<SYNC Start=2000><P Class=KRCC>&nbsp;
</BODY></SAMI>''', encoding="utf-8-sig")
            converter = smi2ass(str(path)).to_ass()
            converter.save(str(root / "output"))
            self.assertEqual(["bilingual-ENG.ass", "bilingual-KOR.ass"],
                             sorted(p.name for p in (root / "output").iterdir()))
            self.assertIn("Hello", (root / "output" / "bilingual-ENG.ass").read_text(encoding="utf-8"))
            self.assertIn("안녕하세요", (root / "output" / "bilingual-KOR.ass").read_text(encoding="utf-8"))
            second = root / "second.smi"
            second.write_text(sample("Next file"), encoding="utf-8")
            converter.to_ass(str(second)).save(root / "output")
            self.assertEqual(["eng"], list(converter.ass_lines))
            self.assertTrue((root / "output" / "second.ass").exists())
            self.assertFalse((root / "output" / "second-KOR.ass").exists())


if __name__ == "__main__":
    unittest.main()
