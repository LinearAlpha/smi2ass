"""Language aliases must preserve legacy codes and separate multilingual output."""
from pathlib import Path
import tempfile
import unittest

from smi2ass import AssStyle, smi2ass
from smi2ass.gui_core import default_settings, inspect_source, prepare_source


class LanguageMappingTest(unittest.TestCase):
    def test_legacy_aliases_and_unknown_fallback_are_preserved(self):
        style = AssStyle(verbose=False)
        expected = {
            "KRCC": "kor", "KOCC": "kor", "KR": "kor", "KO": "kor",
            "KOREANSC": "kor", "KRC": "kor", "ENCC": "eng", "EGCC": "eng",
            "EN": "eng", "EnglishSC": "eng", "ENUSCC": "eng", "ERCC": "eng",
            "CNCC": "chi", "JPCC": "jpn", "UNKNOWNCC": "und",
            "UNKNWN": "und", "COMMENTARY": "commentary", "UnlistedClass": "und",
            # KR/KRCC historically mean Korean here; Kanuri has an unambiguous alias.
            "KAUCC": "kau",
        }
        for alias, language in expected.items():
            with self.subTest(alias=alias):
                self.assertEqual(language, style.get_lang_code(alias.lower()))

    def test_iso_and_regional_aliases_are_case_insensitive(self):
        style = AssStyle(verbose=False)
        groups = {
            "fre": ("FR", "FRCC", "FRE", "FRECC", "FRA", "FRACC", "FRFRCC", "FRCACC"),
            "ger": ("DECC", "GERCC", "DEUCC", "DEDECC"),
            "spa": ("ESCC", "SPACC", "ESESCC", "ESMXCC"),
            "por": ("PTCC", "PORCC", "PTPTCC", "PTBRCC"),
            "chi": ("ZHCC", "CHICC", "ZHOCC", "ZHCNCC", "ZHTWCC"),
            "jpn": ("JACC", "JPNCC", "JAJPCC"),
            "ara": ("ARCC", "ARACC", "ARSACC"),
            "hin": ("HICC", "HINCC", "HIINCC"),
            "vie": ("VICC", "VIECC", "VIVNCC"),
            "tha": ("THCC", "THACC", "THTHCC"),
            "ind": ("IDCC", "INDCC", "IDIDCC"),
            "fil": ("FIL", "FILCC", "FILPHCC"),
            "heb": ("HECC", "HEBCC", "HEILCC"),
            "rus": ("RUCC", "RUSCC", "RURUCC"),
            "swa": ("SWCC", "SWACC"), "zul": ("ZUCC", "ZULCC"),
        }
        for language, aliases in groups.items():
            for alias in aliases:
                with self.subTest(alias=alias):
                    self.assertEqual(language, style.get_lang_code(alias.lower()))

    def test_new_languages_produce_distinct_cli_and_gui_outputs(self):
        captions = {
            "frfrcc": ("fre", "Bonjour à tous."),
            "ESMXCC": ("spa", "¡Hola, buenos días!"),
            "arcc": ("ara", "مرحباً بالعالم"),
            "HIINCC": ("hin", "नमस्ते दुनिया"),
            "vIvNcC": ("vie", "Xin chào thế giới."),
        }
        start = "".join(f"<SYNC Start=1000><P Class={alias}>{text}" for alias, (_, text) in captions.items())
        end = "".join(f"<SYNC Start=2000><P Class={alias}>&nbsp;" for alias in captions)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "languages.smi"
            path.write_text(f"<SAMI><BODY>{start}{end}</BODY></SAMI>", encoding="utf-8-sig")
            smi2ass(str(path), verbose=False).to_ass().save(root / "cli")
            source = inspect_source(path)
            self.assertEqual("", source.error)
            self.assertEqual({lang for lang, _ in captions.values()}, set(source.languages))
            gui = prepare_source(source, default_settings())
            self.assertEqual("", gui.error)
            expected = {f"languages-{language.upper()}.ass" for language, _ in captions.values()}
            self.assertEqual(expected, set(gui.outputs))
            self.assertEqual(expected, {file.name for file in (root / "cli").iterdir()})
            for language, text in captions.values():
                filename = f"languages-{language.upper()}.ass"
                self.assertIn(text, (root / "cli" / filename).read_text(encoding="utf-8"))
                self.assertIn(text, gui.outputs[filename])


if __name__ == "__main__":
    unittest.main()
