"""Load editable defaults and serialize ASS headers in their declared field order."""

import os
import sys
import json
from pathlib import Path

import webcolors


class AssStyle:
    """Own converter style settings, language aliases, and diagnostics.

    Attributes:
        verbose (bool): Whether conversion diagnostics are printed.
        setting_path (Path): Directory containing style and language JSON files.
        lan_code (dict[str, str]): SAMI class aliases mapped to output language codes.
        ass_style (dict): Mutable ScriptInfo and style sections for this instance.
        ass_event (str): Events header matching the converter's Dialogue field order.
    """

    def __init__(self, setting_path: str = "", verbose: bool = True) -> None:
        """Load settings from an override, package, or compiled binary folder.

        Args:
            setting_path (str): Settings directory override. An empty string selects
                packaged or binary-adjacent defaults.
            verbose (bool): Whether to print diagnostics. Defaults to True.

        Raises:
            OSError: A settings file cannot be read.
            json.JSONDecodeError: A settings file contains invalid JSON.
        """

        # Save input path
        self.verbose = verbose
        self.setting_path: Path
        if setting_path == "":
            self.setting_path = Path(__file__).resolve().parent / "setting"
            # Compiled releases prefer editable settings beside the executable.
            if is_nuitka():
                external = Path(sys.argv[0]).resolve().parent / "setting"
                if external.is_dir():
                    self.setting_path = external
        else:
            self.setting_path = Path(setting_path)

        # Reading language code
        self.lan_code: dict[str, str] = load_setting(
            "lan_code.json", self.setting_path
        )

        # Reading ass style information
        self.ass_style: dict[str, any] = load_setting(
            "ass_styles.json", self.setting_path
        )

        # This fixed event schema must match the Dialogue rows produced by the converter.
        self.ass_event: str = (
            "[Events]\nFormat: Layer, Start, End, Style, Actor, MarginL, MarginR, MarginV, Effect, Text\n\n"
        )

    def __compose_info(self) -> str:
        """Compose the ASS Script Info section without mutating its settings.

        Returns:
            str: Script Info header, comments, and key/value records.
        """

        # Read the original mapping without deleting header/comment metadata.
        tmp_dict: dict[str, any] = self.ass_style["ScriptInfo"]

        # Adding heading of info section
        tmp_info: str = str(tmp_dict["Head"]) + "\n"

        # Adding message the info section
        if isinstance(tmp_dict["msg"], list):
            for tmp in tmp_dict["msg"]:
                tmp_info += tmp + "\n"
        else:
            tmp_info += tmp_dict["msg"] + "\n"

        # Instead of deleting used keys, just skip it
        for tmp in tmp_dict.keys():
            if (tmp != "Head") and (tmp != "msg"):
                tmp_info += f"{tmp}: {tmp_dict[tmp]}\n"

        return tmp_info + "\n"  # Separate this section from the following style block.

    def __compose_styles(self) -> str:
        """Compose matching ASS style format and value records in field order.

        Returns:
            str: V4+ Styles section with one Format row and one Style row.
        """

        # Use the same ordered keys for Format and Style so every value matches its field.
        tmp_dict: dict[str, any] = self.ass_style["style"]
        tmp_head: str = tmp_dict["Head"]
        tmp_format: str = "Format: "
        tmp_style: str = "Style: "

        # Settings JSON keeps Head first; it names the section, not a style field.
        for tmp in list(tmp_dict.keys())[1:]:
            tmp_format += f"{tmp}, "
            tmp_style += f"{tmp_dict[tmp]},"

        # ASS records must not end with an extra empty comma-separated field.
        tmp_format = tmp_format[:-2]
        tmp_style = tmp_style[:-1]

        return f"{tmp_head}\n{tmp_format}\n{tmp_style}\n\n"

    def get_lang_code(self, tmp_lang_code: str) -> str:
        """Resolve a SAMI class alias to its shared output language code.

        Args:
            tmp_lang_code (str): SAMI class alias; lookup is case-insensitive.

        Returns:
            str: Mapped language code, or the configured UNKNOWNCC fallback.
        """

        # Class aliases share one output language code for grouping and filename suffixes.
        try:
            return self.lan_code[tmp_lang_code.upper()]
        except:
            self.log(
                'Language code "%s" is not found, please add language code to "%s"'
                % (tmp_lang_code, "lan_code.json")
            )
            return self.lan_code["UNKNOWNCC"]

    def log(self, message: str) -> None:
        """Keep diagnostics optional and usable on legacy Windows consoles.

        Args:
            message (str): Diagnostic text; unencodable characters are escaped for the
                console.
        """
        if not self.verbose:
            return
        try:
            print(message)
        except UnicodeEncodeError:
            # Escape only console diagnostics; Unicode input/output paths stay intact.
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            print(message.encode(encoding, errors="backslashreplace").decode(encoding))

    def color2hex(self, str_color: str) -> str:
        """Return six RGB hex digits without the CSS prefix, ready for BGR conversion.

        Args:
            str_color (str): CSS color name such as red.

        Returns:
            str: Six RGB hex digits without a leading #.

        Raises:
            ValueError: The color name is not recognized by webcolors.
        """
        return webcolors.name_to_hex(str_color).lstrip('#')

    def update_title(self, title: str) -> None:
        """Set the title used in the ASS Script Info section.

        Args:
            title (str): Subtitle/video title to write into the header.
        """

        self.ass_style["ScriptInfo"]["Title"] = title

    @property
    def title(self) -> str:
        """Read the current ASS script title.

        Returns:
            str: Configured Title value.
        """
        return self.ass_style["ScriptInfo"]["Title"]

    def update_res(self, res_x: int, res_y: int) -> None:
        """Set both dimensions of the ASS script canvas.

        Args:
            res_x (int): Horizontal canvas size in pixels.
            res_y (int): Vertical canvas size in pixels.
        """

        self.ass_style["ScriptInfo"]["PlayResX"] = res_x
        self.ass_style["ScriptInfo"]["PlayResY"] = res_y

    @property
    def resolution(self) -> list[int]:
        """Read the current ASS canvas dimensions.

        Returns:
            list[int]: Horizontal and vertical pixel dimensions, in that order.
        """
        return [
            self.ass_style["ScriptInfo"]["PlayResX"],
            self.ass_style["ScriptInfo"]["PlayResY"],
        ]

    def update_font_name(self, name: str) -> None:
        """Set the base font used by the ASS style.

        Args:
            name (str): Font family name expected by the subtitle renderer.
        """

        self.ass_style["style"]["Fontname"] = name

    @property
    def font_name(self) -> str:
        """Read the current base font family.

        Returns:
            str: Configured Fontname value.
        """
        return self.ass_style["style"]["Fontname"]

    def update_font_size(self, size: int | float) -> None:
        """Set the base font size used by the ASS style.

        Args:
            size (int | float): Font size in ASS script coordinates.
        """

        self.ass_style["style"]["Fontsize"] = size

    @property
    def font_size(self) -> int | float:
        """Read the current base font size.

        Returns:
            int | float: Configured Fontsize value.
        """
        return self.ass_style["style"]["Fontsize"]

    def ass_header(self) -> str:
        """Combine script information, style records, and the event schema.

        Returns:
            str: Complete ASS header ready to precede Dialogue records.
        """

        return self.__compose_info() + self.__compose_styles() + self.ass_event


def load_setting(fs_name: str, fs_path: Path | str) -> dict[str, any]:
    """Read fresh UTF-8 JSON settings without sharing mutable mappings.

    Args:
        fs_name (str): JSON filename within the settings directory.
        fs_path (Path | str): Directory containing the requested JSON file.

    Returns:
        dict: Newly decoded settings mapping owned by the caller.

    Raises:
        OSError: The JSON file cannot be read.
        json.JSONDecodeError: The JSON file is malformed.
    """

    file2open = Path(fs_path) / fs_name
    with open(file2open, "r", encoding="utf-8") as f:
        return json.load(f)


def is_nuitka() -> bool:
    """Detect Nuitka compilation or a onefile child process.

    Returns:
        bool: Whether compiled-runtime markers are present.
    """

    # Nuitka exposes a compiled marker; onefile children also inherit the parent marker.
    flag1: bool = "__compiled__" in globals()
    flag2: bool = "NUITKA_ONEFILE_PARENT" in os.environ

    return flag1 or flag2

