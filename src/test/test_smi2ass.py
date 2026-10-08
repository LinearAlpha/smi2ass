"""Regression coverage for CSS color names and ASS's BGR inline color format."""

import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

from smi2ass import AssStyle
from smi2ass import rgb2bgr, smi2ass


class ColorConversionTest(unittest.TestCase):
    """Check both color helpers and the actual markup emitted by conversion."""

    def setUp(self) -> None:
        """Locate checkout settings for color-conversion fixtures."""
        self.setting_path = str(PROJECT_ROOT / "src" / "setting")

    def test_color_name_is_converted_to_six_digit_hex(self) -> None:
        """Verify CSS names resolve to RGB hex digits without their prefix."""
        style = AssStyle(setting_path=self.setting_path)

        self.assertEqual("ff0000", style.color2hex("red"))
        self.assertEqual("0000ff", style.color2hex("blue"))

    def test_rgb_is_converted_to_ass_bgr(self) -> None:
        """Verify RGB bytes are reordered into ASS BGR color values."""
        self.assertEqual("0000ff", rgb2bgr("ff0000"))
        self.assertEqual("00ff00", rgb2bgr("00ff00"))
        self.assertEqual("ff0000", rgb2bgr("0000ff"))

    def test_named_font_color_is_converted_end_to_end(self) -> None:
        """Verify SAMI named colors become valid ASS overrides without #."""
        smi = """<SAMI>
<BODY>
<SYNC Start=1000><P Class=ENCC><FONT COLOR=red>Red text</FONT>
<SYNC Start=2000><P Class=ENCC>&nbsp;
</BODY>
</SAMI>
"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            smi_path = Path(tmp_dir) / "named-color.smi"
            smi_path.write_text(smi, encoding="utf-8")

            converter = smi2ass(
                str(smi_path), setting_path=self.setting_path
            ).to_ass()
            output = "".join(converter.ass_lines["eng"])

        self.assertIn(r"{\c&H0000ff&}Red text{\c}", output)
        # A CSS '#' prefix must not leak into ASS override syntax.
        self.assertNotIn("#", output)


if __name__ == "__main__":
    unittest.main()
