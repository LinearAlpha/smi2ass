"""A lightweight, illustrative ASS style preview (not a libass renderer)."""
from copy import deepcopy

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .gui_core import color_to_rgb


class StylePreview(QWidget):
    """Illustrate ASS styles using Qt font metrics and canvas coordinates.

    Attributes:
        settings (dict | None): Independent ASS settings copy; None paints only the
            background.
        text (str): Sample subtitle text, including optional ASS \\N line breaks.
    """

    def __init__(self, parent=None):
        """Create a preview canvas with default sample text.

        Args:
            parent (QWidget | None): Optional Qt parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.settings = None
        self.text = "Every subtitle, styled your way."
        self.setMinimumHeight(165)
        self.setToolTip("Illustrative preview. Final font metrics and rendering depend on your video player and installed fonts.")

    def set_settings(self, settings):
        """Copy settings for the preview and schedule a repaint.

        Args:
            settings (dict): ASS ScriptInfo and style mappings to illustrate.
        """
        # Preview ownership is separate from the editor/active settings dictionaries.
        self.settings = deepcopy(settings)
        self.update()

    def set_text(self, text):
        """Replace the sample subtitle text and schedule a repaint.

        Args:
            text (str): Preview text; ASS \\N markers are treated as line breaks.
        """
        self.text = text
        self.update()

    def paintEvent(self, event):
        """Paint the background and approximate ASS style with Qt glyph paths.

        Args:
            event (QPaintEvent): Qt paint notification; drawing uses the current widget
                size.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        rect = QRectF(0, 0, width, height)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 10, 10)
        painter.setClipPath(clip)
        sky = QLinearGradient(0, 0, 0, height)
        sky.setColorAt(0, QColor("#c8dce5"))
        sky.setColorAt(.52, QColor("#f2eee2"))
        sky.setColorAt(.53, QColor("#7dacae"))
        sky.setColorAt(1, QColor("#304f59"))
        painter.fillRect(rect, sky)
        # A quiet landscape painted locally: no network or video dependency.
        for color, points in (
            ("#9eb1b7", [(0,.52),(.12,.25),(.25,.44),(.43,.18),(.62,.50),(.78,.30),(1,.50)]),
            ("#697f83", [(0,.56),(.18,.37),(.34,.51),(.56,.33),(.75,.55),(.9,.37),(1,.53)]),
            ("#425f64", [(0,.59),(.08,.45),(.17,.55),(.27,.47),(.42,.58),(.69,.56),(.83,.49),(1,.57)]),
        ):
            path = QPainterPath(QPointF(0, height*.62))
            for x, y in points:
                path.lineTo(width*x, height*y)
            path.lineTo(width, height*.63)
            path.closeSubpath()
            painter.fillPath(path, QColor(color))
        painter.setPen(QPen(QColor(255,255,255,35), 1))
        for index in range(8):
            y = height*(.67 + index*.035)
            painter.drawLine(QPointF(width*.13, y), QPointF(width*.87, y))
        if not self.settings or not self.text:
            return
        style, info = self.settings["style"], self.settings["ScriptInfo"]
        # Fit the ASS canvas inside the widget and scale margins/font size consistently.
        canvas_ratio = info["PlayResX"] / info["PlayResY"]
        canvas_width, canvas_height = width, width / canvas_ratio
        if canvas_height > height:
            canvas_height, canvas_width = height, height * canvas_ratio
        origin_x, origin_y = (width-canvas_width)/2, (height-canvas_height)/2
        factor = canvas_height / info["PlayResY"]
        font = QFont(style["Fontname"])
        font.setPixelSize(max(1, round(style["Fontsize"]*factor)))
        font.setBold(bool(style["Bold"]))
        font.setItalic(bool(style["Italic"]))
        font.setUnderline(bool(style["Underline"]))
        font.setStrikeOut(bool(style["StrikeOut"]))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, style["Spacing"]*factor)
        metrics = QFontMetricsF(font)
        text_path = QPainterPath()
        lines = self.text.replace(r"\N", "\n").splitlines()
        for number, line in enumerate(lines):
            text_path.addText(0, metrics.ascent()+number*metrics.height(), font, line)
        # Decorations are not part of QPainterPath.addText's glyph outlines.
        for number, line in enumerate(lines):
            baseline = metrics.ascent()+number*metrics.height()
            if style["Underline"]:
                text_path.addRect(0, baseline+metrics.underlinePos(), metrics.horizontalAdvance(line), max(.6, factor))
            if style["StrikeOut"]:
                text_path.addRect(0, baseline-metrics.strikeOutPos(), metrics.horizontalAdvance(line), max(.6, factor))
        from PySide6.QtGui import QTransform
        text_path = QTransform().scale(style["ScaleX"]/100, style["ScaleY"]/100).map(text_path)
        bounds = text_path.boundingRect()
        alignment = int(style["Alignment"])
        # ASS alignment uses numpad positions: 1–3 bottom, 4–6 middle, 7–9 top.
        col, row = (alignment-1)%3, (alignment-1)//3
        x = (origin_x + style["MarginL"]*factor if col == 0 else
             origin_x + (canvas_width-bounds.width())/2 if col == 1 else
             origin_x + canvas_width-style["MarginR"]*factor-bounds.width())
        y = (origin_y + canvas_height-style["MarginV"]*factor-bounds.height() if row == 0 else
             origin_y + (canvas_height-bounds.height())/2 if row == 1 else origin_y + style["MarginV"]*factor)
        painter.translate(x-bounds.x(), y-bounds.y())
        painter.rotate(-style["Angle"])

        def color(key):
            """Decode a style color into Qt's RGB and opacity representation.

            Args:
                key (str): ASS style color field to read.

            Returns:
                QColor: RGB color with opacity derived from inverted ASS alpha.
            """
            # QColor's alpha is opacity, opposite to the transparency byte stored by ASS.
            rgb, _ = color_to_rgb(style[key])
            result = QColor(rgb)
            result.setAlpha(255-int(style[key][2:4], 16))
            return result

        shadow = style["Shadow"]*factor
        outline = style["Outline"]*factor
        if style["BorderStyle"] == 3:
            painter.fillRect(bounds.adjusted(-outline, -outline, outline+shadow, outline+shadow), color("OutlineColour"))
        elif shadow:
            painter.save()
            painter.translate(shadow, shadow)
            painter.setPen(QPen(color("BackColour"), outline*2) if outline else Qt.PenStyle.NoPen)
            painter.setBrush(color("BackColour"))
            painter.drawPath(text_path)
            painter.restore()
        painter.setPen(QPen(color("OutlineColour"), outline*2, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                       if outline and style["BorderStyle"] == 1 else Qt.PenStyle.NoPen)
        painter.setBrush(color("PrimaryColour"))
        painter.drawPath(text_path)
        painter.fillPath(text_path, color("PrimaryColour"))
