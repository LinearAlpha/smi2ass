"""Test desktop conversion/settings logic without importing or starting Qt."""

from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from smi2ass.gui_core import (
    PresetStore, color_to_rgb, conflicting_names, default_settings,
    inspect_source, prepare_source, rgb_to_color, validate_settings, write_prepared,
)


def sample(text="Hello", language="ENCC"):
    """Provide one visible cue and a blank end boundary for conversion tests.

    Args:
        text (str): Visible subtitle text for the conversion fixture.
        language (str): SAMI cue class. Defaults to ENCC.

    Returns:
        str: SAMI markup with one visible cue and its blank end boundary.
    """
    return f"<SAMI><BODY><SYNC Start=1000><P Class={language}>{text}<SYNC Start=2000><P Class={language}>&nbsp;</BODY></SAMI>"


class GuiCoreTest(unittest.TestCase):
    """Cover settings validation, timing, persistence, and reviewed output writes."""

    def test_unicode_paths_work_with_legacy_console_encoding(self):
        """Verify Unicode paths with quiet GUI and legacy-console CLI behavior."""
        from smi2ass import smi2ass
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"한글.smi"
            path.write_text(sample(),encoding="utf-8")
            # Simulate a Windows console that cannot encode Korean diagnostic paths.
            console = io.TextIOWrapper(io.BytesIO(),encoding="cp1252")
            with contextlib.redirect_stdout(console):
                source = inspect_source(path)
                self.assertFalse(source.error)
                self.assertFalse(prepare_source(source,default_settings()).error)
                self.assertEqual(0,console.tell())
                smi2ass(str(path)).to_ass().save(Path(directory)/"output")
            self.assertIn("Hello",(Path(directory)/"output"/"한글.ass").read_text(encoding="utf-8"))

    def test_colors_use_ass_bgr_and_inverted_alpha(self):
        """Verify ASS color byte order and opacity round trips."""
        self.assertEqual("&H000000FF", rgb_to_color("#FF0000",100))
        self.assertEqual("&H8000FF00", rgb_to_color("#00FF00",50))
        self.assertEqual(("#00FF00",50),color_to_rgb("&H8000FF00"))
        self.assertEqual("&HFFFFFFFF",rgb_to_color("#FFFFFF",0))

    def test_import_rejects_broken_settings_without_changing_defaults(self):
        """Verify invalid imports are rejected without mutating independent defaults."""
        defaults = default_settings()
        for section,key,value in (("style","Name","bad,name"),("style","Fontsize",-1),
                                   ("style","Outline",float("nan")),("style","PrimaryColour","#FFFFFF"),
                                   ("style","Alignment",0),("ScriptInfo","PlayResX",0),
                                   ("ScriptInfo","Title","bad\nheader")):
            with self.subTest(key=key):
                settings = deepcopy(defaults)
                settings[section][key] = value
                with self.assertRaises(ValueError):
                    validate_settings(settings)
        self.assertEqual(defaults,default_settings())

    def test_presets_and_active_settings_round_trip_and_corrupt_file_recovers(self):
        """Verify preference round trips and recovery from malformed JSON."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"gui.json"
            store = PresetStore(path)
            store.active["style"]["Name"] = "Cinema"
            store.active["style"]["PrimaryColour"] = "&H7F563412"
            store.presets["Cinema"] = deepcopy(store.active)
            store.output = str(Path(directory)/"output")
            store.save()
            restored = PresetStore(path)
            self.assertEqual(store.active,restored.active)
            self.assertEqual(store.presets,restored.presets)
            self.assertEqual(store.output,restored.output)
            path.write_text("broken",encoding="utf-8")
            fallback = PresetStore(path)
            self.assertTrue(fallback.load_error)
            self.assertEqual(default_settings(),fallback.active)

    def test_real_conversion_preserves_legacy_text_and_applies_all_style_fields(self):
        """Verify legacy Korean text, timing, and custom ASS fields reach real output."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"한글 sample.smi"
            text = "안녕하세요. 오늘은 날씨가 맑습니다. 자막 변환을 확인합니다. 함께 영화를 감상해요."
            path.write_bytes(sample(text,"KRCC").encode("cp949"))
            source = inspect_source(path)
            self.assertFalse(source.error)
            self.assertEqual(("kor",),source.languages)
            settings = default_settings()
            settings["style"].update(Name="Cinema",Fontsize=48,Outline=2,MarginV=50,Alignment=8,PrimaryColour="&H8000FF00")
            prepared = prepare_source(source,settings,500)
            self.assertFalse(prepared.error)
            written = write_prepared(prepared,Path(directory)/"output")
            output = written[0].read_text(encoding="utf-8")
            self.assertIn(text,output)
            self.assertIn("Dialogue: 0,0:00:01.50,0:00:02.50,Cinema,",output)
            self.assertIn("Style: Cinema,Malgun Gothic,48,&H8000FF00",output)
            self.assertIn(",2,0,8,12,12,50,1",output)

    def test_unusable_input_and_offset_report_errors(self):
        """Verify unusable input and offsets removing every cue produce error records."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"empty.smi"
            path.write_text("<SAMI></SAMI>",encoding="utf-8")
            self.assertIn("No valid subtitle cues",inspect_source(path).error)
            path.write_text(sample(),encoding="utf-8")
            prepared = prepare_source(inspect_source(path),default_settings(),-10000)
            self.assertTrue(prepared.error)
            self.assertEqual({},prepared.outputs)

    def test_timing_offset_rounds_into_next_second_and_rejects_empty_output(self):
        """Verify centisecond carry, zero starts, and header-only rejection."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"sample.smi"
            path.write_text(sample(),encoding="utf-8")
            source = inspect_source(path)
            # 995 ms exercises centisecond carry; the negative cases test zero and empty output.
            prepared = prepare_source(source,default_settings(),995)
            self.assertIn("0:00:02.00,0:00:03.00",prepared.outputs["sample.ass"])
            at_zero = prepare_source(source,default_settings(),-1000)
            self.assertIn("0:00:00.00,0:00:01.00",at_zero.outputs["sample.ass"])
            self.assertTrue(prepare_source(source,default_settings(),-2000).error)

    def test_zero_start_is_valid_and_invalid_time_is_not_revived_by_offset(self):
        """Verify offsets keep zero starts and reject malformed timestamps."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"sample.smi"
            path.write_text("<SYNC Start=oops><P Class=ENCC>Invalid<SYNC Start=0><P Class=ENCC>Hello<SYNC Start=1000><P Class=ENCC>&nbsp;",encoding="utf-8")
            prepared = prepare_source(inspect_source(path),default_settings(),500)
            self.assertIn("0:00:00.50,0:00:01.50",prepared.outputs["sample.ass"])
            self.assertNotIn("Invalid",prepared.outputs["sample.ass"])

    def test_output_conflicts_and_overwrite_authorization(self):
        """Verify case-insensitive conflicts and exact-path overwrite approval."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = []
            # Distinct source folders and case variants still collide on Windows output names.
            for folder,name in (("a","sample.smi"),("b","SAMPLE.smi")):
                path = root/folder/name
                path.parent.mkdir()
                path.write_text(sample(),encoding="utf-8")
                prepared.append(prepare_source(inspect_source(path),default_settings()))
            self.assertEqual({"sample.ass"},set(conflicting_names(prepared)))
            output = root/"output"
            written = write_prepared(prepared[0],output)
            written[0].write_text("keep me",encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_prepared(prepared[0],output)
            self.assertEqual("keep me",written[0].read_text(encoding="utf-8"))
            write_prepared(prepared[0],output,written)
            self.assertIn("Dialogue:",written[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
