"""Release regressions for installed metadata, bundled defaults, and real file output."""

import contextlib
from importlib.metadata import version
from pathlib import Path
import tempfile
import unittest

from smi2ass import AssStyle, __version__, smi2ass

KOREAN = "안녕하세요. 오늘은 날씨가 맑습니다. 자막 변환을 확인합니다. 함께 영화를 감상해요."


def sample(text, language="ENCC"):
    """Include a terminating blank cue so output timing is deterministic.

    Args:
        text (str): Visible subtitle text for the conversion fixture.
        language (str): SAMI cue class. Defaults to ENCC.

    Returns:
        str: SAMI markup with one visible cue and its blank end boundary.
    """
    return f'''<SAMI><BODY>
<SYNC Start=1000><P Class={language}><FONT COLOR=red>{text}</FONT>
<SYNC Start=2000><P Class={language}>&nbsp;
</BODY></SAMI>'''


class ReleaseRegressionTest(unittest.TestCase):
    """Exercise the installed public API under the same conditions as downloaders."""

    def test_installed_version_matches_cli_version(self):
        """Verify package metadata and the public version match the expected release."""
        self.assertEqual("1.5.1", __version__)
        self.assertEqual(__version__, version("smi2ass"))

    def test_default_settings_are_independent_of_working_directory(self):
        """Verify bundled defaults load when execution starts outside the checkout."""
        with tempfile.TemporaryDirectory() as directory:
            with contextlib.chdir(directory):
                self.assertEqual("kor", AssStyle().get_lang_code("KRCC"))

    def test_legacy_and_unicode_encodings_preserve_text_in_saved_output(self):
        """Verify input encodings preserve text and named colors in ASS output."""
        # Longer Korean text gives encoding detection enough bytes for legacy encodings.
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
        """Verify multilingual naming and state reset when reusing a converter."""
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
            # Reuse the same instance to catch stale language/text state between batch inputs.
            second.write_text(sample("Next file"), encoding="utf-8")
            converter.to_ass(str(second)).save(root / "output")
            self.assertEqual(["eng"], list(converter.ass_lines))
            self.assertTrue((root / "output" / "second.ass").exists())
            self.assertFalse((root / "output" / "second-KOR.ass").exists())


if __name__ == "__main__":
    unittest.main()
