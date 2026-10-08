from copy import deepcopy
from importlib.util import find_spec
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
QT_AVAILABLE = find_spec("PySide6") is not None
if QT_AVAILABLE:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from smi2ass.gui import MainWindow, apply_theme
    from smi2ass.gui_core import PresetStore


@unittest.skipUnless(QT_AVAILABLE,"GUI extra not installed")
class DesktopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.window = MainWindow(self.root/"gui.json")
        self.window.show()
        self.errors = []
        self.window.show_error = self.errors.append

    def wait_idle(self):
        deadline = time.monotonic()+10
        while self.window.busy or self.window.jobs:
            self.app.processEvents()
            if time.monotonic() > deadline:
                self.fail("GUI worker did not finish")
            time.sleep(.01)
        self.app.processEvents()
        self.assertEqual([],self.errors)

    def tearDown(self):
        self.wait_idle()
        self.window.closing = True
        self.window.close()
        self.app.processEvents()
        self.directory.cleanup()

    def add_source(self, folder="", name="sample.smi"):
        path = self.root/folder/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("<SAMI><BODY><SYNC Start=1000><P Class=ENCC>Hello<SYNC Start=2000><P Class=ENCC>&nbsp;</BODY></SAMI>",encoding="utf-8")
        self.window.add_paths([str(path)])
        self.wait_idle()
        return path

    def test_theme_overrides_inherited_dark_palette(self):
        dark = QPalette(self.app.palette())
        dark.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        dark.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        dark.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        self.app.setPalette(dark)
        apply_theme(self.app)
        self.app.processEvents()
        palette = self.window.palette()
        self.assertEqual("#f6f8f9", palette.color(QPalette.ColorRole.Window).name())
        self.assertEqual("#ffffff", self.app.palette().color(QPalette.ColorRole.Base).name())
        self.assertEqual("#26343c", palette.color(QPalette.ColorRole.Text).name())

    def test_dark_theme_switch_persists_without_changing_ass_settings(self):
        original = deepcopy(self.window.active)
        self.window.theme_selector.setCurrentIndex(1)
        self.app.processEvents()
        self.assertEqual("#151d26", self.window.palette().color(QPalette.ColorRole.Window).name())
        self.assertEqual("#e4edf3", self.app.palette().color(QPalette.ColorRole.Text).name())
        self.assertEqual("dark", PresetStore(self.root/"gui.json").theme)
        self.assertEqual(original, self.window.active)
        reopened = MainWindow(self.root/"gui.json")
        self.assertEqual("dark", reopened.theme_selector.currentData())
        reopened.closing = True
        reopened.close()
        self.window.theme_selector.setCurrentIndex(0)
        self.assertEqual("light", PresetStore(self.root/"gui.json").theme)

    def test_settings_apply_persist_and_preview_without_modifying_draft(self):
        editor = self.window.editor
        editor.controls[("style","Name")].setText("Cinema")
        editor.controls[("style","Outline")].setValue(2)
        editor.alignments.button(8).click()
        self.assertEqual(8,editor.preview.settings["style"]["Alignment"])
        self.assertEqual("Default",self.window.active["style"]["Name"])
        self.assertTrue(self.window.apply_settings())
        self.assertEqual("Cinema",PresetStore(self.root/"gui.json").active["style"]["Name"])
        self.assertEqual("Cinema",self.window.convert_preview.settings["style"]["Name"])
        self.assertFalse(editor.preview.grab().isNull())

    def test_selected_rows_convert_and_existing_output_requires_confirmation(self):
        self.add_source(name="first.smi")
        self.add_source(name="second.smi")
        self.window.table.item(1,0).setCheckState(Qt.CheckState.Unchecked)
        self.window.output.setText(str(self.root/"output"))
        self.window.start_conversion()
        self.wait_idle()
        path = self.root/"output"/"first.ass"
        self.assertTrue(path.exists())
        self.assertFalse((path.parent/"second.ass").exists())
        path.write_text("keep me",encoding="utf-8")
        with patch.object(QMessageBox,"exec",return_value=QMessageBox.StandardButton.Cancel):
            self.window.start_conversion()
            self.wait_idle()
        self.assertEqual("keep me",path.read_text(encoding="utf-8"))
        with patch.object(QMessageBox,"exec",return_value=QMessageBox.StandardButton.Yes):
            self.window.start_conversion()
            self.wait_idle()
        self.assertIn("Hello",path.read_text(encoding="utf-8"))

    def test_duplicate_output_names_are_blocked_and_cancel_writes_nothing(self):
        self.add_source("a")
        self.add_source("b")
        self.window.output.setText(str(self.root/"output"))
        self.window.start_conversion()
        self.wait_idle()
        self.assertFalse((self.root/"output"/"sample.ass").exists())
        self.assertEqual("Error",self.window.table.item(0,3).text())
        self.window.start_conversion()
        self.window.cancel_work()
        self.wait_idle()
        self.assertFalse((self.root/"output"/"sample.ass").exists())
        self.assertIn("Cancelled",self.window.status.text())

    def test_failed_input_stays_visible_and_is_not_selectable(self):
        path = self.root/"broken.smi"
        path.write_text("not subtitles",encoding="utf-8")
        self.window.add_paths([str(path)])
        self.wait_idle()
        self.assertEqual("Error",self.window.table.item(0,3).text())
        self.assertFalse(self.window.convert_button.isEnabled())
        self.assertTrue(self.window.table.item(0,3).toolTip())

    def test_json_export_and_import_restore_editor_settings(self):
        path = self.root/"ass_styles.json"
        editor = self.window.editor
        editor.controls[("style","Fontsize")].setValue(48)
        expected = deepcopy(editor.settings)
        with patch.object(QFileDialog,"getSaveFileName",return_value=(str(path),"")):
            self.window.export_settings()
        editor.set_settings(self.window.active)
        with patch.object(QFileDialog,"getOpenFileName",return_value=(str(path),"")):
            self.window.import_settings()
        self.assertEqual(expected,editor.settings)
        self.assertEqual(64,self.window.active["style"]["Fontsize"])


if __name__ == "__main__":
    unittest.main()
