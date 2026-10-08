"""ASS settings editor shared by the desktop window and GUI tests."""
from copy import deepcopy

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup, QColorDialog, QComboBox, QDoubleSpinBox, QFontComboBox,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .gui_core import color_to_rgb, rgb_to_color
from .gui_preview import StylePreview


def label(text, role=""):
    """Create a wrapping label whose object-name role selects shared theme styling."""
    widget = QLabel(text)
    if role:
        widget.setObjectName(role)
    widget.setWordWrap(True)
    return widget


def button(text, callback=None, primary=False):
    """Create a consistently styled action button with an optional click handler."""
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName("primary")
    if callback:
        widget.clicked.connect(callback)
    return widget


def card(title=""):
    """Return a themed container and its layout for assembling settings sections."""
    widget = QFrame()
    widget.setObjectName("card")
    layout = QVBoxLayout(widget)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "section"))
    return widget, layout


class ColorControl(QWidget):
    """Present an ASS color as an RGB swatch and a user-facing opacity percentage."""
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.value = "&H00FFFFFF"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.swatch = button("#FFFFFF", self.choose)
        self.swatch.setMinimumWidth(112)
        self.opacity = QSpinBox()
        self.opacity.setRange(0,100)
        self.opacity.setSuffix(" %")
        self.opacity.setToolTip("Opacity: 100% is fully visible.")
        layout.addWidget(self.swatch, 1)
        layout.addWidget(self.opacity)
        self.opacity.valueChanged.connect(self.opacity_changed)

    def set_value(self, value):
        self.value = value
        rgb, opacity = color_to_rgb(value)
        self.swatch.setText(rgb)
        self.swatch.setStyleSheet(f"QPushButton {{ border-left: 12px solid {rgb}; }}")
        # Updating the spinbox from an ASS value must not emit another color edit.
        self.opacity.blockSignals(True)
        self.opacity.setValue(opacity)
        self.opacity.blockSignals(False)

    def choose(self):
        selected = QColorDialog.getColor(QColor(color_to_rgb(self.value)[0]), self, "Choose subtitle color")
        if selected.isValid():
            self.set_value(rgb_to_color(selected.name(), self.opacity.value()))
            self.changed.emit(self.value)

    def opacity_changed(self, opacity):
        self.set_value(rgb_to_color(color_to_rgb(self.value)[0], opacity))
        self.changed.emit(self.value)


class SettingsEditor(QWidget):
    """Edit a settings draft and update its preview without applying it to conversion."""
    changed = Signal(dict)

    def __init__(self, settings):
        super().__init__()
        self.settings = deepcopy(settings)
        self.controls = {}
        self.loading = True
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(22)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0,0,5,0)
        left_layout.setSpacing(16)
        scroll.setWidget(left)
        layout.addWidget(scroll, 4)
        appearance, body = card("Style & font")
        form = QFormLayout()
        form.setSpacing(12)
        self.add_text(form, "Style name", "style", "Name")
        font = QFontComboBox()
        font.setEditable(True)
        self.register(font, "style", "Fontname")
        font.currentTextChanged.connect(lambda value: self.update_value("style", "Fontname", value))
        form.addRow("Font", font)
        self.add_number(form, "Size (px)", "style", "Fontsize", 1, 1000)
        toggles = QHBoxLayout()
        for name, text in (("Bold","B"),("Italic","I"),("Underline","U"),("StrikeOut","S")):
            toggle = button(text)
            toggle.setCheckable(True)
            toggle.setToolTip(name)
            toggle.setAccessibleName(name)
            toggle.setMaximumWidth(50)
            self.register(toggle, "style", name)
            # Capture each field name at connection time; ASS uses -1 for enabled emphasis.
            toggle.toggled.connect(lambda checked, key=name: self.update_value("style",key,-1 if checked else 0))
            toggles.addWidget(toggle)
        toggles.addStretch()
        form.addRow("Emphasis", toggles)
        body.addLayout(form)
        left_layout.addWidget(appearance)
        colors, body = card("Colors")
        form = QFormLayout()
        form.setSpacing(10)
        for name, text in (("PrimaryColour","Text"),("SecondaryColour","Secondary"),("OutlineColour","Outline"),("BackColour","Shadow")):
            control = ColorControl()
            self.register(control, "style", name)
            control.changed.connect(lambda value, key=name: self.update_value("style",key,value))
            form.addRow(text, control)
        body.addLayout(form)
        left_layout.addWidget(colors)
        border, body = card("Border & shadow")
        form = QFormLayout()
        mode = QComboBox()
        mode.addItem("Outline",1)
        mode.addItem("Opaque box",3)
        self.register(mode,"style","BorderStyle")
        mode.currentIndexChanged.connect(lambda _: self.update_value("style","BorderStyle",mode.currentData()))
        form.addRow("Border mode",mode)
        self.add_number(form,"Outline (px)","style","Outline",0,100)
        self.add_number(form,"Shadow (px)","style","Shadow",0,100)
        body.addLayout(form)
        left_layout.addWidget(border)
        advanced, body = card()
        expand = button("Advanced style options  ▾")
        expand.setCheckable(True)
        body.addWidget(expand)
        advanced_content = QWidget()
        form = QFormLayout(advanced_content)
        form.setContentsMargins(0,0,0,0)
        for key, text, low, high in (
            ("ScaleX","Width scale (%)",1,1000),("ScaleY","Height scale (%)",1,1000),
            ("Spacing","Letter spacing (px)",-100,100),("Angle","Rotation (°)",-360,360),
            ("Encoding","Font encoding",0,255),
        ):
            self.add_number(form,text,"style",key,low,high,integer=key=="Encoding")
        self.add_text(form,"Script title","ScriptInfo","Title")
        self.add_number(form,"Timer (%)","ScriptInfo","Timer",1,1000)
        for key, text, values in (("ScaledBorderAndShadow","Scale border & shadow",("Yes","No")),("Collisions","Collision handling",("Normal","Reverse"))):
            control = QComboBox()
            control.addItems(values)
            self.register(control,"ScriptInfo",key)
            control.currentTextChanged.connect(lambda value, key=key: self.update_value("ScriptInfo",key,value))
            form.addRow(text,control)
        advanced_content.setVisible(False)
        expand.toggled.connect(advanced_content.setVisible)
        body.addWidget(advanced_content)
        left_layout.addWidget(advanced)
        left_layout.addStretch()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(16)
        preview_card, body = card("Live preview")
        self.preview = StylePreview()
        self.preview.setMinimumHeight(260)
        body.addWidget(self.preview)
        self.preview_text = QLineEdit("Every subtitle, styled your way.")
        self.preview_text.setAccessibleName("Preview text")
        self.preview_text.textChanged.connect(self.preview.set_text)
        body.addWidget(label("Preview text", "muted"))
        body.addWidget(self.preview_text)
        body.addWidget(label("Illustrative preview · Your video player determines final rendering.", "muted"))
        right_layout.addWidget(preview_card, 1)
        positioning, body = card("Position & canvas")
        row = QHBoxLayout()
        alignment_box = QWidget()
        grid = QGridLayout(alignment_box)
        grid.setContentsMargins(0,0,0,0)
        self.alignments = QButtonGroup(self)
        self.alignments.setExclusive(True)
        # ASS numbers follow a numpad: display 7–9 at the top while retaining their IDs.
        for number in range(1,10):
            control = button("•")
            control.setCheckable(True)
            control.setFixedSize(42,32)
            control.setAccessibleName(f"Alignment {number}")
            control.setToolTip(f"ASS alignment {number}")
            grid.addWidget(control,2-(number-1)//3,(number-1)%3)
            self.alignments.addButton(control,number)
        self.alignments.idClicked.connect(lambda number:self.update_value("style","Alignment",number))
        row.addWidget(alignment_box)
        row.addSpacing(20)
        form = QFormLayout()
        for key,text in (("MarginL","Left (px)"),("MarginR","Right (px)"),("MarginV","Vertical (px)")):
            self.add_number(form,text,"style",key,0,10000,integer=True)
        row.addLayout(form,1)
        body.addLayout(row)
        canvas = QFormLayout()
        self.add_number(canvas,"Canvas width","ScriptInfo","PlayResX",1,16384,integer=True)
        self.add_number(canvas,"Canvas height","ScriptInfo","PlayResY",1,16384,integer=True)
        body.addLayout(canvas)
        right_layout.addWidget(positioning)
        right_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setWidget(right)
        layout.addWidget(right_scroll,6)
        self.set_settings(settings)

    def register(self, widget, section, key):
        # Bind controls to the JSON section/key used by import, export, and reset.
        widget.setObjectName(key)
        self.controls[(section,key)] = widget

    def add_text(self, form, text, section, key):
        widget = QLineEdit()
        self.register(widget,section,key)
        widget.textChanged.connect(lambda value:self.update_value(section,key,value))
        form.addRow(text,widget)

    def add_number(self, form, text, section, key, low, high, integer=False):
        widget = QSpinBox() if integer else QDoubleSpinBox()
        if not integer:
            widget.setDecimals(2)
        widget.setRange(low,high)
        self.register(widget,section,key)
        widget.valueChanged.connect(lambda value:self.update_value(section,key,value))
        form.addRow(text,widget)

    def update_value(self, section, key, value):
        """Update only the draft and emit a copy so observers cannot mutate editor state."""
        if self.loading:
            return
        self.settings[section][key] = value
        self.preview.set_settings(self.settings)
        self.changed.emit(deepcopy(self.settings))

    def set_settings(self, settings):
        # Signals still fire while populating controls; the loading guard ignores them.
        self.loading = True
        self.settings = deepcopy(settings)
        for (section,key), control in self.controls.items():
            value = settings[section][key]
            if isinstance(control, ColorControl):
                control.set_value(value)
            elif isinstance(control,QFontComboBox):
                control.setCurrentFont(QFont(value))
                control.setEditText(value)
            elif isinstance(control,QLineEdit):
                control.setText(value)
            elif isinstance(control,QPushButton):
                control.setChecked(bool(value))
            elif isinstance(control,QComboBox):
                if key == "BorderStyle":
                    control.setCurrentIndex(control.findData(value))
                else:
                    control.setCurrentText(value)
            else:
                control.setValue(value)
        self.alignments.button(int(settings["style"]["Alignment"])).setChecked(True)
        self.preview.set_settings(settings)
        self.loading = False
