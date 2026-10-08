"""Qt-independent settings, presets, and conversion operations for the desktop UI."""
from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
import tempfile

from .ass_settings import AssStyle
from .smi2ass import smi2ass


def default_settings():
    return deepcopy(AssStyle().ass_style)


def validate_settings(value):
    """Return a complete, ordered ASS configuration or reject invalid imports."""
    defaults = default_settings()
    if not isinstance(value, dict):
        raise ValueError("Settings must be a JSON object with ScriptInfo and style sections.")
    for section in defaults:
        if not isinstance(value.get(section), dict):
            raise ValueError(f"Missing {section} section.")
        unknown = set(value[section]) - set(defaults[section])
        if unknown:
            raise ValueError(f"Unsupported {section} fields: {', '.join(sorted(unknown))}")
        defaults[section].update(value[section])
    style, info = defaults["style"], defaults["ScriptInfo"]
    for key in ("Name", "Fontname"):
        if not isinstance(style[key], str) or not style[key].strip() or any(c in style[key] for c in ",\r\n"):
            raise ValueError(f"{key} must be nonempty and cannot contain commas or line breaks.")
    limits = {
        "Fontsize": (1, 1000), "ScaleX": (1, 1000), "ScaleY": (1, 1000),
        "Spacing": (-100, 100), "Angle": (-360, 360), "Outline": (0, 100),
        "Shadow": (0, 100), "MarginL": (0, 10000), "MarginR": (0, 10000),
        "MarginV": (0, 10000), "Encoding": (0, 255),
    }
    for key, (low, high) in limits.items():
        number = style[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not low <= number <= high:
            raise ValueError(f"{key} must be between {low} and {high}.")
    for key in ("MarginL", "MarginR", "MarginV", "Encoding"):
        if int(style[key]) != style[key]:
            raise ValueError(f"{key} must be a whole number.")
        style[key] = int(style[key])
    for key in ("Bold", "Italic", "Underline", "StrikeOut"):
        if type(style[key]) is not int or style[key] not in (-1, 0, 1):
            raise ValueError(f"Invalid {key} flag.")
    if type(style["Alignment"]) is not int or style["Alignment"] not in range(1, 10) or type(style["BorderStyle"]) is not int or style["BorderStyle"] not in (1, 3):
        raise ValueError("Invalid alignment or border mode.")
    for key in ("PrimaryColour", "SecondaryColour", "OutlineColour", "BackColour"):
        if not isinstance(style[key], str) or not re.fullmatch(r"&H[0-9a-fA-F]{8}", style[key]):
            raise ValueError(f"{key} must be an ASS color such as &H00FFFFFF.")
    for key in ("PlayResX", "PlayResY"):
        if type(info[key]) is not int or not 1 <= info[key] <= 16384:
            raise ValueError(f"{key} must be a whole number between 1 and 16384.")
    if info["ScaledBorderAndShadow"] not in ("Yes", "No") or info["Collisions"] not in ("Normal", "Reverse"):
        raise ValueError("Invalid script options.")
    if not isinstance(info["Timer"], (int, float)) or not math.isfinite(info["Timer"]) or not 1 <= info["Timer"] <= 1000:
        raise ValueError("Timer must be between 1 and 1000.")
    if not isinstance(info["Title"], str) or any(c in info["Title"] for c in "\r\n"):
        raise ValueError("Title cannot contain line breaks.")
    if info["ScriptType"] != "v4.00+" or type(info["PlayDepth"]) is not int or info["PlayDepth"] not in (0,8,16,24,32):
        raise ValueError("Invalid ASS script type or play depth.")
    messages = info["msg"] if isinstance(info["msg"], list) else [info["msg"]]
    if not all(isinstance(message,str) and message.startswith(";") and not any(c in message for c in "\r\n") for message in messages):
        raise ValueError("Script comments must be single lines starting with a semicolon.")
    # Preserve the converter's expected section headers and field order.
    for section in defaults:
        defaults[section]["Head"] = "[Script Info]" if section == "ScriptInfo" else "[V4+ Styles]"
    return defaults


def color_to_rgb(value):
    alpha, blue, green, red = (int(value[index:index + 2], 16) for index in (2, 4, 6, 8))
    return f"#{red:02X}{green:02X}{blue:02X}", round((255 - alpha) * 100 / 255)


def rgb_to_color(rgb, opacity):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", rgb) or not 0 <= opacity <= 100:
        raise ValueError("Invalid color or opacity.")
    alpha = round(255 * (1 - opacity / 100))
    return f"&H{alpha:02X}{rgb[5:7]}{rgb[3:5]}{rgb[1:3]}".upper()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class PresetStore:
    def __init__(self, path):
        self.path = Path(path)
        self.active = default_settings()
        self.presets = {"Default": deepcopy(self.active)}
        self.output = str(Path.home() / "Subtitles")
        self.open_output = False
        self.theme = "light"
        self.load_error = ""
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.active = validate_settings(data["active"])
                self.presets.update({name: validate_settings(settings) for name, settings in data["presets"].items() if name != "Default"})
                self.output = str(data.get("output", self.output))
                self.open_output = bool(data.get("open_output", False))
                self.theme = "dark" if data.get("theme") == "dark" else "light"
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                self.active = default_settings()
                self.presets = {"Default": deepcopy(self.active)}
                self.load_error = f"Saved settings could not be loaded. Defaults are in use.\n{error}"

    def save(self):
        write_json(self.path, {"active": validate_settings(self.active), "presets": self.presets,
                              "output": self.output, "open_output": self.open_output, "theme": self.theme})


@dataclass
class Source:
    path: Path
    languages: tuple[str, ...] = ()
    encoding: str = ""
    error: str = ""


def inspect_source(path):
    path = Path(path).resolve()
    try:
        converter = smi2ass(str(path), verbose=False)
        return Source(path, tuple(converter.smi_lines), converter.encoding or "Unknown")
    except (OSError, ValueError, IndexError, TypeError) as error:
        return Source(path, error=str(error))


@dataclass
class Prepared:
    source: Source
    outputs: dict[str, str] = field(default_factory=dict)
    error: str = ""


def prepare_source(source, settings, offset=0):
    try:
        converter = smi2ass(verbose=False)
        converter.ass_style = validate_settings(settings)
        converter.set_time_offset(offset)
        converter.to_ass(str(source.path))
        outputs = {}
        for language, lines in converter.ass_lines.items():
            suffix = f"-{language.upper()}" if len(converter.ass_lines) > 1 else ""
            outputs[f"{source.path.stem}{suffix}.ass"] = "".join(lines)
        if not outputs or not any(len(lines) > 1 for lines in converter.ass_lines.values()):
            raise ValueError("No subtitle cues remain after applying the timing offset.")
        return Prepared(source, outputs)
    except Exception as error:
        return Prepared(source, error=str(error))


def conflicting_names(prepared):
    owners = {}
    for item in prepared:
        for filename in item.outputs:
            owners.setdefault(filename.casefold(), []).append(item.source.path)
    return {name: paths for name, paths in owners.items() if len(paths) > 1}


def write_prepared(item, folder, overwrite=()):
    """Never replace an existing file unless its exact path was approved."""
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    allowed = {Path(path).resolve() for path in overwrite}
    written = []
    for filename, contents in item.outputs.items():
        path = folder / filename
        # Exclusive creation also handles files appearing after the confirmation.
        mode = "w" if path in allowed else "x"
        with path.open(mode, encoding="utf-8", newline="") as file:
            file.write(contents)
        written.append(path)
    return written
