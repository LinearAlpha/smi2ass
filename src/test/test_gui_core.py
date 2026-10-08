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
    return f"<SAMI><BODY><SYNC Start=1000><P Class={language}>{text}<SYNC Start=2000><P Class={language}>&nbsp;</BODY></SAMI>"


class GuiCoreTest(unittest.TestCase):
    def test_unicode_paths_work_with_legacy_console_encoding(self):
        from smi2ass import smi2ass
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"한글.smi"
            path.write_text(sample(),encoding="utf-8")
            console = io.TextIOWrapper(io.BytesIO(),encoding="cp1252")
            with contextlib.redirect_stdout(console):
                source = inspect_source(path)
                self.assertFalse(source.error)
                self.assertFalse(prepare_source(source,default_settings()).error)
                self.assertEqual(0,console.tell())
                smi2ass(str(path)).to_ass().save(Path(directory)/"output")
            self.assertIn("Hello",(Path(directory)/"output"/"한글.ass").read_text(encoding="utf-8"))

    def test_colors_use_ass_bgr_and_inverted_alpha(self):
        self.assertEqual("&H000000FF", rgb_to_color("#FF0000",100))
        self.assertEqual("&H8000FF00", rgb_to_color("#00FF00",50))
        self.assertEqual(("#00FF00",50),color_to_rgb("&H8000FF00"))
        self.assertEqual("&HFFFFFFFF",rgb_to_color("#FFFFFF",0))

    def test_import_rejects_broken_settings_without_changing_defaults(self):
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
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"empty.smi"
            path.write_text("<SAMI></SAMI>",encoding="utf-8")
            self.assertIn("No valid subtitle cues",inspect_source(path).error)
            path.write_text(sample(),encoding="utf-8")
            prepared = prepare_source(inspect_source(path),default_settings(),-10000)
            self.assertTrue(prepared.error)
            self.assertEqual({},prepared.outputs)

    def test_timing_offset_rounds_into_next_second_and_rejects_empty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"sample.smi"
            path.write_text(sample(),encoding="utf-8")
            source = inspect_source(path)
            prepared = prepare_source(source,default_settings(),995)
            self.assertIn("0:00:02.00,0:00:03.00",prepared.outputs["sample.ass"])
            self.assertTrue(prepare_source(source,default_settings(),-1000).error)

    def test_output_conflicts_and_overwrite_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = []
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
