# Python builtin modules
import os
import sys
import json
from pathlib import Path

# PIP installed modules
import webcolors


class AssStyle:
    def __init__(self, setting_path: str = "", verbose: bool = True) -> None:
        """Reads setting JSON file form local drive and compose into ASS
        header block. Also, reads language code and color code setting from
        JSON file from local drive that can convert SMI to ASS style code.

        Args:
            setting_path (str, optional): Path to where JSON files are located.
            Defaults to packaged settings, or settings beside the executable.
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

        # Prepare even block of the ass header
        self.ass_event: str = (
            "[Events]\nFormat: Layer, Start, End, Style, Actor, MarginL, MarginR, MarginV, Effect, Text\n\n"
        )

    def __compose_info(self) -> str:
        """Composing "Script Info" block of ASS header in string

        Returns:
            str: Composed "Script Info" block of subtitle
        """

        # Shallow copy to protect original data
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

        return tmp_info + "\n"  # Back to home!! LOL

    def __compose_styles(self) -> str:
        """Compose "Styles" block of AAS header in string

        Returns:
            str: Composed "Styles" block
        """

        # Shallow copy to protect original data
        tmp_dict: dict[str, any] = self.ass_style["style"]
        tmp_head: str = tmp_dict["Head"]
        tmp_format: str = "Format: "
        tmp_style: str = "Style: "

        # Instead of deleting used keys, just skip it
        for tmp in list(tmp_dict.keys())[1:]:
            # if tmp != "Head":
            tmp_format += f"{tmp}, "
            tmp_style += f"{tmp_dict[tmp]},"

        # Remove "," to avoid when feed into video
        tmp_format = tmp_format[:-2]
        tmp_style = tmp_style[:-1]

        return f"{tmp_head}\n{tmp_format}\n{tmp_style}\n\n"

    def get_lang_code(self, tmp_lang_code: str) -> str:
        """Convert SMI language code to ASS language code

        Args:
            tmp_lang_code (str): SMI language code in all upper case

        Returns:
            str: Matching ASS language code. in case when language code is not
            exist, it will return "und" as unknown
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
        """Keep diagnostics optional and usable on legacy Windows consoles."""
        if not self.verbose:
            return
        try:
            print(message)
        except UnicodeEncodeError:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            print(message.encode(encoding, errors="backslashreplace").decode(encoding))

    def color2hex(self, str_color: str) -> str:
        return webcolors.name_to_hex(str_color).lstrip('#') # it can get rid of '#' in front of the hex code

    def update_title(self, title: str) -> None:
        """Update title value in the Script Info block

        Args:
            title (str): Name of Video file that where subtitle will be used
        """

        self.ass_style["ScriptInfo"]["Title"] = title

    @property
    def title(self) -> str:
        return self.ass_style["ScriptInfo"]["Title"]

    def update_res(self, res_x: int, res_y: int) -> None:
        """To update resolution information of the video. It is default to
        FullHD (1920 x 1080) resolution in the json file

        Args:
            res_x (int): Horizontal size of the screen
            res_y (int): Vertical size of the screen
        """

        self.ass_style["ScriptInfo"]["PlayResX"] = res_x
        self.ass_style["ScriptInfo"]["PlayResY"] = res_y

    @property
    def resolution(self) -> list[int]:
        return [
            self.ass_style["ScriptInfo"]["PlayResX"],
            self.ass_style["ScriptInfo"]["PlayResY"],
        ]

    def update_font_name(self, name: str) -> None:
        """Updating font of subtitle

        Args:
            name (str): Name of the Font
        """

        self.ass_style["style"]["Fontname"] = name

    @property
    def font_name(self) -> str:
        return self.ass_style["style"]["Fontname"]

    def update_font_size(self, size: int | float) -> None:
        """Updating font size of subtitle

        Args:
            size (int | float): Size of font
        """

        self.ass_style["style"]["Fontsize"] = size

    @property
    def font_size(self) -> int | float:
        return self.ass_style["style"]["Fontsize"]

    def ass_header(self) -> str:
        """Composing ASS header that contains ASS style settings

        Returns:
            str: Composed ASS header in string format
        """

        return self.__compose_info() + self.__compose_styles() + self.ass_event


def load_setting(fs_name: str, fs_path: Path | str) -> dict[str, any]:
    """Reading json file from file

    Args:
        fs_name (str): JSON file name
        fs_path (str): Path to JSON file

    Returns:
        dict[str, any]: Parsed JSON data from file
    """

    file2open = Path(fs_path) / fs_name
    with open(file2open, "r", encoding="utf-8") as f:
        return json.load(f)


def is_nuitka() -> bool:
    """Check if the script is compiled with Nuitka

    Returns:
        bool: True, if compiled with Nuitka
    """

    flag1: bool = "__compiled__" in globals()
    flag2: bool = "NUITKA_ONEFILE_PARENT" in os.environ

    return flag1 or flag2

