"""Exercise the real desktop flow, also inside compiled/extracted executables."""
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QPalette

from .gui import MainWindow
from .gui_core import PresetStore, write_json


def run_smoke(app, report):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        input_file = root / "bilingual.smi"
        input_file.write_text('''<SAMI><BODY>
<SYNC Start=1000><P Class=ENCC>Hello
<SYNC Start=1000><P Class=KRCC>안녕하세요
<SYNC Start=2000><P Class=ENCC>&nbsp;
<SYNC Start=2000><P Class=KRCC>&nbsp;
</BODY></SAMI>''', encoding="utf-8-sig")
        window = MainWindow(root / "gui.json")
        failures = []
        window.show_error = failures.append
        window.show()
        window.editor.controls[("style","Name")].setText("Cinema")
        window.editor.controls[("style","Fontsize")].setValue(48)
        window.editor.controls[("style","MarginV")].setValue(50)
        window.store.presets["Cinema"] = window.editor.settings.copy()
        window.apply_settings()
        window.output.setText(str(root / "output"))
        window.offset.setValue(500)
        window.add_paths([str(input_file)])
        phase = ["inspect"]
        deadline = time.monotonic()+45
        timer = QTimer()

        def check():
            try:
                if failures:
                    raise AssertionError("\n".join(failures))
                if time.monotonic() > deadline:
                    raise TimeoutError("GUI operation did not finish within 45 seconds.")
                if window.busy or window.jobs:
                    return
                if phase[0] == "inspect":
                    window.theme_selector.setCurrentIndex(1)
                    assert app.palette().color(QPalette.ColorRole.Window).name() == "#151d26"
                    assert PresetStore(root / "gui.json").theme == "dark"
                    for filename in ("arrow-up.svg", "arrow-down.svg", "arrow-up-dark.svg", "arrow-down-dark.svg", "check.svg"):
                        icon = QIcon(str(Path(__file__).resolve().parent / "gui_icons" / filename))
                        assert not icon.pixmap(15, 15).isNull(), filename
                    window.theme_selector.setCurrentIndex(0)
                    assert app.palette().color(QPalette.ColorRole.Window).name() == "#f6f8f9"
                    assert len(window.sources) == 1
                    assert window.sources[0].languages == ("eng","kor")
                    assert window.convert_button.isEnabled()
                    window.start_conversion()
                    phase[0] = "convert"
                    return
                files = sorted((root / "output").glob("*.ass"))
                assert [path.name for path in files] == ["bilingual-ENG.ass","bilingual-KOR.ass"]
                for path in files:
                    text = path.read_text(encoding="utf-8")
                    assert "Style: Cinema," in text
                    assert "0:00:01.50,0:00:02.50,Cinema," in text
                assert "Hello" in files[0].read_text(encoding="utf-8")
                assert "안녕하세요" in files[1].read_text(encoding="utf-8")
                saved = PresetStore(root / "gui.json")
                assert saved.active["style"]["Name"] == "Cinema"
                assert saved.active["style"]["MarginV"] == 50
                assert "Cinema" in saved.presets
                write_json(report,{"ok":True,"checks":["Qt startup","queue inspection","settings apply",
                    "preset persistence","light/dark themes","packaged control icons",
                    "background conversion","timing offset","multilingual output"]})
                timer.stop()
                app.exit(0)
            except Exception as error:
                write_json(report,{"ok":False,"error":repr(error)})
                timer.stop()
                app.exit(1)

        timer.timeout.connect(check)
        timer.start(20)
        code = app.exec()
        window.closing = True
        window.close()
        return code
