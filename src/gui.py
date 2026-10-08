"""Native desktop interface. Launch with smi2ass-gui or python -m smi2ass.gui."""
from copy import deepcopy
from pathlib import Path
import sys
import threading

from . import __version__
from .gui_launcher import main


STYLESHEET = """
QWidget { font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; color: #26343c; }
QMainWindow, QWidget#page { background: #f6f8f9; }
QFrame#card { background: white; border: 1px solid #dfe5e8; border-radius: 12px; }
QLabel { background: transparent; border: none; }
QLabel#title { font-size: 27px; font-weight: 600; }
QLabel#brand { font-size: 20px; font-weight: 600; color: #087e91; }
QLabel#section { font-size: 15px; font-weight: 600; }
QLabel#muted { color: #697983; font-size: 12px; }
QLabel#dirty { color: #9c6a24; background: #fff2d7; padding: 5px 10px; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #d6dfe4; border-radius: 6px; padding: 7px 12px; }
QPushButton:hover { background: #edf6f8; border-color: #78b5c0; }
QPushButton:checked { background: #dff2f5; border-color: #11869a; color: #087184; }
QPushButton#primary { background: #087f95; color: white; border-color: #087f95; font-weight: 600; padding: 10px 22px; }
QPushButton#primary:hover { background: #096a7b; }
QPushButton:disabled { background: #eef1f3; color: #96a1a9; border-color: #e3e7e9; }
QPushButton#primary:disabled { background: #dce8eb; color: #83939b; border-color: #dce8eb; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #d6dfe4; border-radius: 6px; padding: 6px; min-height: 20px; }
QComboBox, QSpinBox, QDoubleSpinBox { padding-right: 30px; }
QComboBox::drop-down { subcontrol-origin: border; subcontrol-position: top right; width: 26px; border: none; border-left: 1px solid #e3e9ec; }
QComboBox::down-arrow { image: url("@ICONS@/arrow-down.svg"); width: 12px; height: 8px; }
QComboBox QAbstractItemView { background: white; color: #26343c; selection-background-color: #dff2f5; selection-color: #087184; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 24px; background: #f4f8f9; border-left: 1px solid #e3e9ec; border-bottom: 1px solid #e3e9ec; border-top-right-radius: 6px; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; background: #f4f8f9; border-left: 1px solid #e3e9ec; border-bottom-right-radius: 6px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("@ICONS@/arrow-up.svg"); width: 12px; height: 8px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("@ICONS@/arrow-down.svg"); width: 12px; height: 8px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #11869a; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 12px 24px; color: #65757f; background: transparent; border-bottom: 3px solid transparent; }
QTabBar::tab:selected { color: #087f95; border-bottom-color: #087f95; font-weight: 600; }
QTableWidget { border: none; background: white; gridline-color: #edf0f2; selection-background-color: #e8f5f7; selection-color: #26343c; }
QHeaderView::section { background: #f5f8f9; color: #6a7881; padding: 9px; border: none; font-weight: 500; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator, QAbstractItemView::indicator { width: 15px; height: 15px; background: white; border: 1px solid #b5c4cc; border-radius: 3px; }
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked { background: #087f95; border-color: #087f95; image: url("@ICONS@/check.svg"); }
QProgressBar { border: none; border-radius: 3px; background: #e4ecef; height: 6px; text-align: center; }
QProgressBar::chunk { background: #11869a; border-radius: 3px; }
QScrollArea { background: #f6f8f9; }
QScrollBar:vertical { width: 9px; background: transparent; }
QScrollBar::handle:vertical { background: #d1dce1; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; background: transparent; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""
STYLESHEET = STYLESHEET.replace("@ICONS@", (Path(__file__).resolve().parent / "gui_icons").as_posix())


# Keep the CLI and --version usable without Qt installed.
try:
    from PySide6.QtCore import QStandardPaths, QThread, QTimer, Qt, QUrl, Signal
    from PySide6.QtGui import QColor, QDesktopServices, QPalette
    from PySide6.QtWidgets import (
        QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
        QHeaderView, QInputDialog, QLayout, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
        QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    )
    from .gui_core import (
        PresetStore, color_to_rgb, conflicting_names, default_settings, inspect_source,
        prepare_source, validate_settings, write_json, write_prepared,
    )
    from .gui_preview import StylePreview
    from .gui_settings import SettingsEditor, button, card, label
except ImportError:
    if __name__ == "__main__":
        raise SystemExit(main())
    raise


def apply_theme(app):
    """Use a complete light palette, even when Windows uses a dark theme."""
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#f6f8f9",
        QPalette.ColorRole.WindowText: "#26343c",
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#f5f8f9",
        QPalette.ColorRole.Text: "#26343c",
        QPalette.ColorRole.Button: "#ffffff",
        QPalette.ColorRole.ButtonText: "#26343c",
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Highlight: "#087f95",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: "#087f95",
        QPalette.ColorRole.LinkVisited: "#087184",
        QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: "#26343c",
        QPalette.ColorRole.PlaceholderText: "#697983",
        QPalette.ColorRole.Light: "#ffffff",
        QPalette.ColorRole.Midlight: "#edf2f4",
        QPalette.ColorRole.Mid: "#d6dfe4",
        QPalette.ColorRole.Dark: "#a4b2ba",
        QPalette.ColorRole.Shadow: "#697983",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#96a1a9"))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)


class Job(QThread):
    update = Signal(object, str, object)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, work, cancel):
        super().__init__()
        self.work, self.cancel = work, cancel

    def run(self):
        try:
            self.result.emit(self.work(self))
        except Exception as error:
            self.error.emit(str(error))


class DropZone(QFrame):
    paths = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self.setStyleSheet("QFrame#dropZone { background: #f5fafb; border: 1px dashed #9fc7d0; border-radius: 8px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12,14,12,14)
        title = label("↓   Drop .smi files here", "section")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = label("SAMI subtitle files · .smi and .sami", "muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.paths.emit([url.toLocalFile() for url in event.mimeData().urls()])
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        self.setWindowTitle(f"smi2ass · {__version__}")
        self.resize(1180, 960)
        self.setMinimumSize(980, 720)
        path = config_path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / "gui.json"
        self.store = PresetStore(path)
        self.active = deepcopy(self.store.active)
        self.sources = []
        self.jobs = set()
        self.busy = False
        self.closing = False
        self.cancel = threading.Event()
        root = QWidget()
        root.setObjectName("page")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30,18,30,22)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(label("▤  smi2ass", "brand"))
        header.addStretch()
        header.addWidget(label("SAMI → ASS", "muted"))
        layout.addLayout(header)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.make_convert_page(), "Convert")
        self.tabs.addTab(self.make_settings_page(), "ASS Settings")
        layout.addWidget(self.tabs, 1)
        self.refresh_presets()
        self.refresh_summary()
        if self.store.load_error:
            QTimer.singleShot(0, lambda: self.show_error(self.store.load_error))

    def make_convert_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,18,0,0)
        layout.setSpacing(16)
        layout.addWidget(label("Convert subtitles", "title"))
        layout.addWidget(label("Add SAMI files, choose your style, and convert to ASS.", "muted"))
        columns = QHBoxLayout()
        columns.setSpacing(22)
        self.input_panel = QWidget()
        left = QVBoxLayout(self.input_panel)
        left.setContentsMargins(0,0,0,0)
        left.setSpacing(16)
        sources, body = card("Source files")
        tools = QHBoxLayout()
        tools.addWidget(button("Add files", self.add_files))
        tools.addWidget(button("Add folder", self.add_folder))
        tools.addStretch()
        tools.addWidget(button("Clear list", self.clear_sources))
        body.addLayout(tools)
        drop = DropZone()
        drop.paths.connect(self.add_paths)
        body.addWidget(drop)
        self.table = QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["File", "Languages", "Encoding", "Status", ""])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for column,width in ((1,90),(2,90),(3,95),(4,38)):
            self.table.setColumnWidth(column,width)
        self.table.setMinimumHeight(160)
        self.table.itemChanged.connect(lambda _: self.refresh_summary())
        body.addWidget(self.table,1)
        self.queue_summary = label("Add files to get started.", "muted")
        body.addWidget(self.queue_summary)
        left.addWidget(sources,1)
        output, body = card("Output")
        row = QHBoxLayout()
        self.output = QLineEdit(self.store.output)
        self.output.setAccessibleName("Output folder")
        self.output.setPlaceholderText("Choose an output folder")
        row.addWidget(self.output,1)
        row.addWidget(button("Browse…",self.browse_output))
        body.addLayout(row)
        self.open_output = QCheckBox("Open output folder after conversion")
        self.open_output.setChecked(self.store.open_output)
        body.addWidget(self.open_output)
        body.addWidget(label("One ASS file per language · name.ass or name-ENG.ass / name-KOR.ass", "muted"))
        left.addWidget(output)
        timing, body = card("Timing")
        row = QHBoxLayout()
        row.addWidget(label("Offset"))
        self.offset = QSpinBox()
        self.offset.setRange(-86400000,86400000)
        self.offset.setSuffix(" ms")
        self.offset.setAccessibleName("Timing offset")
        row.addWidget(self.offset)
        row.addStretch()
        body.addLayout(row)
        body.addWidget(label("Positive values delay subtitles. Negative values advance them.", "muted"))
        left.addWidget(timing)
        columns.addWidget(self.input_panel, 7)
        style_card, body = card("ASS style")
        body.addWidget(label("Preset", "muted"))
        self.preset = QComboBox()
        self.preset.setAccessibleName("ASS style preset")
        self.preset.currentTextChanged.connect(self.select_preset)
        body.addWidget(self.preset)
        self.convert_preview = StylePreview()
        self.convert_preview.setMinimumHeight(190)
        body.addWidget(self.convert_preview)
        self.style_summary = label("")
        self.style_summary.setStyleSheet("line-height: 1.5;")
        body.addWidget(self.style_summary)
        body.addWidget(button("Edit ASS settings",lambda:self.tabs.setCurrentIndex(1)))
        body.addWidget(label("Settings are applied to every selected file.\nInline styling in the SAMI file can override the base style.", "muted"))
        body.addStretch()
        columns.addWidget(style_card, 3)
        self.style_card = style_card
        content = QWidget()
        content.setLayout(columns)
        columns.setContentsMargins(0,0,5,0)
        columns.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        layout.addWidget(scroll,1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        footer = QHBoxLayout()
        self.status = label("Ready", "muted")
        footer.addWidget(self.status,1)
        self.cancel_button = button("Cancel", self.cancel_work)
        self.cancel_button.hide()
        footer.addWidget(self.cancel_button)
        self.convert_button = button("Convert files", self.start_conversion, primary=True)
        self.convert_button.setEnabled(False)
        footer.addWidget(self.convert_button)
        layout.addLayout(footer)
        return page

    def make_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,18,0,0)
        layout.setSpacing(16)
        row = QHBoxLayout()
        row.addWidget(label("ASS Settings", "title"))
        row.addStretch()
        self.dirty = label("Unsaved changes", "dirty")
        self.dirty.hide()
        row.addWidget(self.dirty)
        layout.addLayout(row)
        layout.addWidget(label("Customize your subtitle style and preview the result.", "muted"))
        self.editor = SettingsEditor(self.active)
        self.editor.changed.connect(lambda _: self.dirty.setVisible(self.editor.settings != self.active))
        layout.addWidget(self.editor,1)
        row = QHBoxLayout()
        row.addWidget(button("Reset defaults",self.reset_settings))
        row.addWidget(button("Import settings",self.import_settings))
        row.addWidget(button("Export settings",self.export_settings))
        row.addStretch()
        row.addWidget(button("Save preset",self.save_preset))
        row.addWidget(button("Apply to conversion",self.apply_settings,primary=True))
        layout.addLayout(row)
        return page

    def show_error(self, text):
        QMessageBox.warning(self,"smi2ass",text)

    def persist(self):
        self.store.active = deepcopy(self.active)
        self.store.output = self.output.text()
        self.store.open_output = self.open_output.isChecked()
        try:
            self.store.save()
            return True
        except (OSError, ValueError) as error:
            self.show_error(f"Preferences could not be saved.\n{error}")
            return False

    def refresh_presets(self):
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItem("Custom")
        self.preset.addItems(self.store.presets)
        match = next((name for name,value in self.store.presets.items() if value == self.active),"Custom")
        self.preset.setCurrentText(match)
        self.preset.blockSignals(False)

    def select_preset(self,name):
        if name not in self.store.presets:
            return
        if self.editor.settings != self.active and not self.discard_draft():
            self.refresh_presets()
            return
        self.active = deepcopy(self.store.presets[name])
        self.editor.set_settings(self.active)
        self.dirty.hide()
        self.persist()
        self.refresh_summary()

    def discard_draft(self):
        return QMessageBox.question(self,"Discard changes?","Discard the unapplied ASS settings changes?",
                                    QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,
                                    QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Discard

    def apply_settings(self):
        try:
            self.active = validate_settings(self.editor.settings)
        except ValueError as error:
            self.show_error(str(error))
            return False
        self.editor.set_settings(self.active)
        self.dirty.hide()
        self.persist()
        self.refresh_presets()
        self.refresh_summary()
        self.tabs.setCurrentIndex(0)
        return True

    def reset_settings(self):
        if self.editor.settings != self.active and not self.discard_draft():
            return
        self.editor.set_settings(default_settings())
        self.dirty.setVisible(self.editor.settings != self.active)

    def import_settings(self):
        import json
        path,_ = QFileDialog.getOpenFileName(self,"Import ASS settings","","JSON settings (*.json)")
        if not path:
            return
        try:
            settings = validate_settings(json.loads(Path(path).read_text(encoding="utf-8-sig")))
            if self.editor.settings != self.active and not self.discard_draft():
                return
            self.editor.set_settings(settings)
            self.dirty.setVisible(settings != self.active)
        except (OSError,ValueError) as error:
            self.show_error(f"Could not import settings.\n{error}")

    def export_settings(self):
        try:
            settings = validate_settings(self.editor.settings)
            path,_ = QFileDialog.getSaveFileName(self,"Export ASS settings","ass_styles.json","JSON settings (*.json)")
            if path:
                write_json(path,settings)
        except (OSError,ValueError) as error:
            self.show_error(f"Could not export settings.\n{error}")

    def save_preset(self):
        name,ok = QInputDialog.getText(self,"Save preset","Preset name")
        name = name.strip()
        if not ok or not name:
            return
        if name in ("Default","Custom"):
            self.show_error("Choose a name other than Default or Custom.")
            return
        if name in self.store.presets and QMessageBox.question(self,"Replace preset?",f'Replace "{name}"?') != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.presets[name] = validate_settings(self.editor.settings)
            self.apply_settings()
        except ValueError as error:
            self.show_error(str(error))

    def selected_sources(self):
        return [source for row,source in enumerate(self.sources)
                if not source.error and self.table.item(row,0).checkState() == Qt.CheckState.Checked]

    def refresh_summary(self):
        selected = self.selected_sources()
        count = len(selected)
        outputs = sum(len(source.languages) for source in selected)
        self.queue_summary.setText(f"{count} selected · {outputs} ASS output files" if self.sources else "Add files to get started.")
        self.convert_button.setText(f"Convert {count} file{'s' if count != 1 else ''}")
        self.convert_button.setEnabled(bool(count) and not self.busy)
        style,info = self.active["style"],self.active["ScriptInfo"]
        alignment = ("Bottom left","Bottom center","Bottom right","Middle left","Center","Middle right","Top left","Top center","Top right")[int(style["Alignment"])-1]
        self.style_summary.setText(f"Font     {style['Fontname']}\nSize     {style['Fontsize']:g} px\nText     {color_to_rgb(style['PrimaryColour'])[0]}\nOutline  {style['Outline']:g} px\nPosition {alignment}\nCanvas   {info['PlayResX']} × {info['PlayResY']}")
        self.convert_preview.set_settings(self.active)

    def add_files(self):
        paths,_ = QFileDialog.getOpenFileNames(self,"Add SAMI files","","SAMI subtitles (*.smi *.sami *.SMI *.SAMI)")
        self.add_paths(paths)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self,"Add folder")
        if folder:
            self.add_paths([folder])

    def add_paths(self, paths):
        if self.busy or not paths:
            return
        known = {source.path for source in self.sources}
        def inspect(job):
            found = set()
            for raw in paths:
                path = Path(raw)
                candidates = path.rglob("*") if path.is_dir() else [path]
                for candidate in candidates:
                    if job.cancel.is_set():
                        return None
                    if candidate.suffix.lower() not in (".smi",".sami") or not candidate.is_file():
                        continue
                    candidate = candidate.resolve()
                    if candidate in known or candidate in found:
                        continue
                    found.add(candidate)
                    source = inspect_source(candidate)
                    job.update.emit(source,"add",None)
            return None
        self.status.setText("Reading subtitle files…")
        self.start_job(inspect,self.inspection_done)

    def inspection_done(self, _):
        self.set_busy(False)
        self.status.setText("Ready" if self.sources else "No SAMI files found.")

    def handle_update(self,source,status,extra):
        if status == "add":
            row = len(self.sources)
            self.sources.append(source)
            self.table.insertRow(row)
            file_item = QTableWidgetItem(source.path.name)
            file_item.setToolTip(str(source.path))
            file_item.setCheckState(Qt.CheckState.Unchecked if source.error else Qt.CheckState.Checked)
            if source.error:
                file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            # Suppress itemChanged while the new row is incomplete.
            self.table.blockSignals(True)
            self.table.setItem(row,0,file_item)
            self.table.setItem(row,1,QTableWidgetItem(", ".join(language.upper() for language in source.languages)))
            self.table.setItem(row,2,QTableWidgetItem(source.encoding.upper().replace("_","-")))
            self.table.setItem(row,3,QTableWidgetItem("Error" if source.error else "Ready"))
            self.table.item(row,3).setToolTip(source.error)
            remove = button("×",lambda _,source=source:self.remove_source(source))
            remove.setAccessibleName(f"Remove {source.path.name}")
            self.table.setCellWidget(row,4,remove)
            self.table.setRowHeight(row,43)
            self.table.blockSignals(False)
            self.refresh_summary()
            return
        row = self.sources.index(source)
        self.table.item(row,3).setText(status)
        self.table.item(row,3).setToolTip(str(extra or ""))
        self.status.setText(f"{source.path.name} · {status}")
        if isinstance(extra,int):
            self.progress.setValue(extra)

    def remove_source(self,source):
        if self.busy:
            return
        row = self.sources.index(source)
        self.table.blockSignals(True)
        self.table.removeRow(row)
        self.sources.pop(row)
        self.table.blockSignals(False)
        self.refresh_summary()

    def clear_sources(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.sources.clear()
        self.table.blockSignals(False)
        self.refresh_summary()

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self,"Output folder",self.output.text())
        if folder:
            self.output.setText(folder)

    def set_busy(self,busy):
        self.busy = busy
        self.input_panel.setEnabled(not busy)
        self.style_card.setEnabled(not busy)
        self.tabs.setTabEnabled(1,not busy)
        self.progress.setVisible(busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        self.refresh_summary()

    def start_job(self,work,result):
        self.cancel = threading.Event()
        self.set_busy(True)
        job = Job(work,self.cancel)
        self.jobs.add(job)
        job.update.connect(self.handle_update)
        job.result.connect(result)
        job.error.connect(self.job_failed)
        job.finished.connect(lambda:self.finish_job(job))
        job.start()

    def finish_job(self,job):
        self.jobs.discard(job)
        job.deleteLater()
        if self.closing and not self.jobs:
            self.set_busy(False)
            self.close()

    def job_failed(self,error):
        self.set_busy(False)
        self.status.setText("Operation failed")
        self.show_error(error)

    def cancel_work(self):
        self.cancel.set()
        self.cancel_button.setEnabled(False)
        self.status.setText("Cancelling after the current file…")

    def start_conversion(self):
        sources = self.selected_sources()
        if not sources or self.busy:
            return
        if not self.output.text().strip():
            self.show_error("Choose an output folder first.")
            return
        if self.editor.settings != self.active:
            answer = QMessageBox.question(self,"Apply settings?","Apply your ASS settings changes before converting?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|QMessageBox.StandardButton.Cancel)
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Yes and not self.apply_settings():
                return
        self.persist()
        settings,offset = deepcopy(self.active),self.offset.value()
        self.progress.setRange(0,len(sources)*2)
        self.progress.setValue(0)
        def prepare(job):
            prepared = []
            for index,source in enumerate(sources):
                if job.cancel.is_set():
                    break
                job.update.emit(source,"Converting",None)
                item = prepare_source(source,settings,offset)
                prepared.append(item)
                job.update.emit(source,"Error" if item.error else "Prepared",item.error or index+1)
            return prepared
        self.start_job(prepare,self.prepared_done)

    def prepared_done(self,prepared):
        if self.cancel.is_set() or self.closing:
            self.set_busy(False)
            self.status.setText("Cancelled · no output files written")
            return
        duplicates = conflicting_names(prepared)
        blocked = {path for paths in duplicates.values() for path in paths}
        for item in prepared:
            if item.source.path in blocked:
                item.error = "Output filename conflicts with another source. Convert these files to separate folders."
                self.handle_update(item.source,"Error",item.error)
        folder = Path(self.output.text()).expanduser().resolve()
        valid = [item for item in prepared if not item.error]
        existing = [folder/name for item in valid for name in item.outputs if (folder/name).exists()]
        if existing:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Replace output files?")
            dialog.setText(f"{len(existing)} output file(s) already exist. Replace them?")
            dialog.setDetailedText("\n".join(str(path) for path in existing))
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel)
            dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if dialog.exec() != QMessageBox.StandardButton.Yes:
                self.set_busy(False)
                self.status.setText("Cancelled · existing files were kept")
                return
        def save(job):
            written,errors = [], [item.error for item in prepared if item.error]
            for index,item in enumerate(valid):
                if job.cancel.is_set():
                    break
                try:
                    outputs = write_prepared(item,folder,existing)
                    written.extend(outputs)
                    job.update.emit(item.source,"Done",len(prepared)+index+1)
                except Exception as error:
                    errors.append(str(error))
                    job.update.emit(item.source,"Error",str(error))
            return written,errors,job.cancel.is_set(),folder
        self.start_job(save,self.conversion_done)

    def conversion_done(self,result):
        written,errors,cancelled,folder = result
        self.set_busy(False)
        self.status.setText(f"{'Cancelled' if cancelled else 'Completed'} · {len(written)} ASS files saved" + (f" · {len(errors)} file errors (see row details)" if errors else ""))
        if written and self.open_output.isChecked() and not self.closing:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def closeEvent(self,event):
        if self.busy or self.jobs:
            if QMessageBox.question(self,"Cancel and close?","Cancel the current operation and close after the current file finishes?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.closing = True
                self.cancel_work()
            event.ignore()
            return
        if not self.closing and self.editor.settings != self.active and not self.discard_draft():
            event.ignore()
            return
        self.persist()
        event.accept()


if __name__ == "__main__":
    raise SystemExit(main())
