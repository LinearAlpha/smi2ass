# Python built in modules
import re
from typing import Self
from collections import defaultdict
from operator import itemgetter
from pathlib import Path
import html

# PIP installed modules
import charset_normalizer as chardet
from bs4 import BeautifulSoup as bs
from bs4 import ResultSet

# Custom modules
from ass_settings import AssStyle


class smi2ass(AssStyle):
    def __init__(self, smi_path: str = "", **kwargs) -> None:
        """Class constructor, this class only initializes when SMI file path
        is given as input variable

        Args:
            smi_path (str, optional): Smi file path. Defaults to "".
        """

        # Initializing parent class
        super().__init__(**kwargs)

        self.path2smi: Path  # Path to SMI file
        self.smi_sgml: str
        self.smi_sgml_bs: ResultSet
        # The value that  hold smi lines by each language. The language code
        # is used as key of the dictionary.
        # Each dictionary key is holding list as [lines, time code in ass]
        self.smi_lines: dict[str, list[any]] = defaultdict(list)
        # The value that holds converted lines from SMI subtitle. The language
        # will be used as key of the dictionary.
        # Each key will hold list as [lines of ass formatted subtitle]
        self.ass_lines: dict[str, list[str]] = defaultdict(list)
        # Flag initialization process is complete before converting to ASS
        self.flag_preprocess: bool = False

        # Setting time offset from original file
        self.flag_time_offset: bool = False
        self.time_offset: int = 0

        # Only initialize the class when SMI file path is provided
        if smi_path != "":
            self.__preprocess(smi_path)

    def __preprocess(self, smi_file_input: str) -> None:
        """Initializing class by provided SMI file path.
        This function read SMI file, clean white space and parse SMI subtitle
        with HTML parser.

        Args:
            smi_path (str): SMI file path

        Raises:
            IOError: Neither file is not exist or cannot access file
        """

        self.path2smi = Path(smi_file_input)  # Saving input path

        # Printing which file is currently converting
        print(f"\nConverting... \n{self.path2smi}")

        # Check if file is accessible. If it is not, program will raise error.
        try:
            # Identify encoding of the file
            with open(smi_file_input, "rb") as f:
                f_encoding: str | None = chardet.detect(f.read())["encoding"]
            # Reading SMI file
            with open(
                smi_file_input, "r", encoding=f_encoding, errors="replace"
            ) as f:
                self.smi_sgml = f.read()
        except IOError as e:
            raise IOError(f"Failed to open the file {smi_file_input}: {e}")

        # Preprocess raw string before parse SMI lines
        self.__convert_whitespace()
        self.__convert_ss()
        self.__add_sync_tag()

        # Parse SMI with BeautifulSoup with HTML parser
        self.smi_sgml_bs = bs(self.smi_sgml, "html.parser").find_all("sync")

        # Get timecode for each lines and septate out subtitle in each language
        self.__time_lan()

        # Preprocess is complete, not it can convert to ass
        self.flag_preprocess = True

    def __convert_whitespace(self) -> None:
        """Converting CRLF, LF or TAB to white space."""

        # Some subtitle uses TAB as space character
        whitespace: list[str] = ["\u000D\u000A", "\u000A", "\u000D"]

        # CRLF, LF to a whitespace
        for temp in whitespace:
            self.smi_sgml.replace(temp, " ")

        # TAB to whitespace
        self.smi_sgml.replace("\t", "    ")

    def __convert_ss(self) -> None:
        """Converting special characters to ASCII code with defined flag, so
        it can convert correctly at the end.
        """

        # Defining special characters in unicode
        char_ss: list[str] = [
            "\u00A0",
            "\u180E",
            "\u2000",
            "\u2001",
            "\u2002",
            "\u2003",
            "\u2004",
            "\u2005",
            "\u2006",
            "\u2007",
            "\u2008",
            "\u2009",
            "\u200A",
            "\u200B",
            "\u202F",
            "\u205F",
            "\u3000",
        ]

        # Replace special space characters so that Beautifulsoup
        # can't remove them
        for tmp_ss in char_ss:
            self.smi_sgml.replace(
                tmp_ss, f"smi2ass_unicode({str(ord(tmp_ss))})"
            )

        # Replace space around a tag with "&nbsp;", so that they are not
        # stripped when we replace a tag.
        self.smi_sgml = re.sub(r"> +<", ">smi2ass_unicode(32)<", self.smi_sgml)
        self.smi_sgml = re.sub(r"> +", ">smi2ass_unicode(32)", self.smi_sgml)
        self.smi_sgml = re.sub(r" +<", "smi2ass_unicode(32)<", self.smi_sgml)

        # but not <rt>
        self.smi_sgml = re.sub(
            r"< *[Rr][Tt] *>(smi2ass_unicode\([0-9]+\))+",
            "<rt>",
            self.smi_sgml,
        )
        self.smi_sgml = re.sub(
            r"(smi2ass_unicode\([0-9]+\))+</ *[Rr][Tt] *>",
            "</rt>",
            self.smi_sgml,
        )

    def __add_sync_tag(self) -> None:
        """Closing the <sync> tags to avoid tag recursion when it is parses by
        BeautifulSoup
        """

        # Remove </sync>
        self.smi_sgml = re.sub(r"</ *[Ss][Yy][Nn][Cc] *>", "", self.smi_sgml)
        # Add </sync> right before <sync>
        self.smi_sgml = re.sub(
            r"< *[Ss][Yy][Nn][Cc] +", "</sync><sync ", self.smi_sgml
        )

    def __ms2timestamp(self, ms: int) -> str:
        """Converting millisecond to h:mm:ss.ff time format

        Args:
            ms (int): Time in millisecond

        Returns:
            str: Converted time stamp
        """

        hours = int(ms / 3600000)
        ms -= hours * 3600000
        minutes = int(ms / 60000)
        ms -= minutes * 60000
        seconds = int(ms / 1000)
        ms -= seconds * 1000
        ms = round(ms / 10)
        return "%01d:%02d:%02d.%02d" % (hours, minutes, seconds, ms)

    def __time_lan(self) -> None:
        """Form original SMI file, get timecode in millisecond and in case
        of the subtitle contained multiple language separate out for each
        language.

        If language is less then 10% compare with largest language, it might
        be misuse of class name tag on SMI subtile.
        Thus, in that case this function will be merge language to largest
        """

        tmp_lines: dict[str, list[any]] = defaultdict(list)
        time_code: int  # Prepare valuable to hold time in ms.

        # Set for timecode and separate out each language
        for lines in self.smi_sgml_bs:

            # Language separation is depends on p class tag (<P Class= >)
            # Get language name from <P Class= > tag
            try:
                lang_tag: list[str] = lines.find("p")["class"]
            except:  # Bad case: <SYNC Start=7630><P>
                # If no p class, it will set to unknown language
                lang_tag = ["UNKNOWNCC"]
                print(f"Failed to extract language class: {lines}")
                print('Language has been set to "UNKNOWNCC"')

            # for index, lines in enumerate(self.smi_sgml_bs):
            # Get timecode from <SYNC Start= > tag
            # If case when there is error, the time_code is set to "-1"
            try:
                # original code uses regular expression to get timecode. Based
                # on some sample SMIs, it seems not need to use regular
                # expression
                # time_code = int(re.sub(r'\..*$', '', lines['start']))
                time_code = int(lines["start"])
                if time_code < 0:
                    time_code = -1
                    print(f"Negative time code: \n\n{lines}\n")
            except:
                time_code = -1
                print(f"Failed to extract time code: \n\n{lines}\n")

            # Adjust subtitle timecode based on the offset input
            if self.flag_time_offset:
                time_code += self.time_offset

            # The key of the dictionary is language code in ass.
            # temporarily hols smi line data in to tmp_lines, and data
            # structure is [smi lines, ass time code, time in ms]
            if time_code > 0:
                ass_lang_code: str = self.get_lang_code(lang_tag[0].upper())
                tmp_lines[ass_lang_code].append(
                    [lines, self.__ms2timestamp(time_code), time_code]
                )

        # Sort the dictionary by the length of the list associated with
        # each key
        tmp_lines = dict(
            sorted(tmp_lines.items(), key=lambda item: len(item[1]))
        )

        # Prepare list to hold language code and present of language compare
        # with largest language.
        # line_count structure: [lan code: str, percent: float]
        line_count: list[any] = []
        # First key from the dictionary, which has largest lines.
        tmp_key: str = list(tmp_lines.keys())[0]
        for tmp_lang in tmp_lines.keys():
            tmp_len: int = len(tmp_lines[tmp_lang])
            line_count.append(
                [tmp_lang, tmp_len, tmp_len / len(tmp_lines[tmp_key])]
            )

        if len(line_count) != 1:
            for tmp in line_count:
                tmp_key: str = tmp[0]
                # If language is less then or equal to 10%, merge to largest
                if tmp[2] <= 0.1:
                    tmp_lines[line_count[0]] += tmp_lines[tmp_key]
                    del tmp_lines[tmp_key]

        # Sort each language lines based on SMI timecode in millisecond
        for key, value in tmp_lines.items():
            # Sorting lines by SMI timecode only more then one language
            if len(tmp_lines) != 1:
                tmp_lines[key] = sorted(value, key=itemgetter(2))

        # Copy temperate value to the class values
        self.smi_lines = tmp_lines

    def __tag_conv(self, tags: list[any], conv_rule: str) -> None:
        """Converting SMI tags to ASS format based on input rule

        Args:
            tags (list[any]): SMI tags that is found in line.
            conv_rule (str): Conversion rule that in C string format. It must
            only include one string position. (e.g "example %s test")
        """

        for tmp_tag in tags:
            if len(tmp_tag.text) != 0:
                tmp_tag.replaceWith(conv_rule % tmp_tag.text)
            else:
                tmp_tag.extract()

    def __core(self, lines2conv: list[list[any]]) -> list[str]:
        # Setting first item to be ASS style header
        tmp_ass_lines: list[str] = [self.ass_header()]

        for i in range(len(lines2conv)):
            # Getting current line of SMI
            tmp_line: bs = lines2conv[i][0]

            # Setting converted timecode
            track_start: str = lines2conv[i][1]  # Start time of subtitle

            # Setting end time code
            try:
                track_end: str = lines2conv[i + 1][1]  # End time of subtitles
            except:
                """
                Due to how the SMI subtitle is structure, there isn't
                indication for end time for the line. Thus, adding 1s to the
                last time code, os it cant convert without error
                """
                track_end: str = self.__ms2timestamp(lines2conv[i][2] + 1000)

            # Converting next line (br) tags
            for tmp_br in tmp_line.find_all("br"):
                tmp_br.replaceWith("\\N")

            # Convert bold (b) tags
            self.__tag_conv(tmp_line.find_all("b"), "{\\b1}%s{\\b0}")

            # Convert italics (i) tag
            self.__tag_conv(tmp_line.find_all("i"), "{\\i1}%s{\\i0}")

            # Convert underline (u) tag
            self.__tag_conv(tmp_line.find_all("u"), "{\\u1}%s{\\u0}")

            # Convert strikes (s) tag
            self.__tag_conv(tmp_line.find_all("s"), "{\\s1}%s{\\s0}")

            # Convert ruby (rt) tag
            self.__tag_conv(
                tmp_line.find_all("s"),
                "{\\fscx50}{\\fscy50}&nbsp;%s&nbsp;{\\fscx100}{\\fscy100}",
            )

            # Convert font color to ass format
            for tmp_color in tmp_line.find_all("font"):
                try:  # Try ro parse color from SMI line
                    # Parse color from the SMI line
                    smi_col: str = tmp_color["color"].lower()

                    # Prepare conversion rule to ass in "C" string style
                    convt_rule: str = "{\\c&H%s&}%s{\\c}"
                    # Prepare valuable to save line
                    convt_line: str = ""

                    # Try to get color code in hex, if it is not in hex, the
                    # search function returns "None"
                    hexcolor: re.Match[str] | None = re.search(
                        "[0-9a-fA-F]{6}", smi_col
                    )

                    # Case when hex color code found
                    if hexcolor != None:
                        convt_line = convt_rule % (
                            rgb2bgr(hexcolor.group(0)),
                            tmp_color.text,
                        )
                    else:  # Case when color name is given (e.g green)
                        try:  # Try if color name is in CSS3 color DB
                            convt_line = convt_rule % (
                                rgb2bgr(self.color2hex(smi_col)),
                                tmp_color.text,
                            )
                        except:  # Failed to convert
                            convt_line = tmp_color.text
                            print(f"Failed to convert color name: {smi_col}")

                    # Update with converted line
                    tmp_color.replaceWith(convt_line)
                except:  # Bad case: '<font size=30>'
                    pass

            # Get converted line
            contents: str = tmp_line.text

            # Converting place holder to actual character
            contents = re.sub(
                r"smi2ass_unicode\(([0-9]+)\)", r"&#\1;", contents
            )

            # Converting ASCII to special character
            contents = html.unescape(contents)

            # Removes next line character to avoid error when it sets loading
            contents = re.sub("\n", "", contents, len(contents) - 1)

            # Only add converted line when there is content
            if len(contents.strip()) != 0:
                tmp_ass_lines.append(
                    "Dialogue: 0,%s,%s,Default,,0000,0000,0000,,%s\n"
                    % (track_start, track_end, contents)
                )

        return tmp_ass_lines

    def update_file2conv(self, smi_path: str) -> Self:
        """Re-initialing class with new SMI file

        Args:
            smi_path (str): SMI file path

        Returns:
            Self: Returning itself
        """

        self.__preprocess(smi_path)

        return self

    def set_time_offset(self, offset: int) -> None:
        self.flag_time_offset = True
        self.time_offset = offset

    def to_ass(self, smi_path: str = "") -> Self:
        """Converting SMI subtitle to ASS

        Args:
            smi_path (str, optional): In case when need to update file to
            convert. Defaults to "".

        Returns:
            Self: Returning itself
        """

        # If there is path input then update to new SMI file
        if smi_path != "":
            self.update_file2conv(smi_path)

        # If class was not initialized print error message.
        if not self.flag_preprocess:
            print(
                "Initialization  process is not completed\n"
                + 'Please Initialize class by calling "update_file2conv" method'
            )
        else:
            for key, value in self.smi_lines.items():
                self.ass_lines[key] = self.__core(value)

        return self

    def save(self, path2save: str | Path = "") -> None:
        """Save converted subtitle into the drive. If output path was not
        provided it will save into where is SMI file located

        Args:
            path2save (str | Path, optional): Input path. Defaults to "".
        """

        ass_path: Path  # Preparing value to hole output path

        if type(path2save) == str:
            if path2save == "":
                ass_path = self.path2smi.parents[0]
            else:
                ass_path = Path(path2save)
                ass_path.mkdir(parents=True, exist_ok=True)
        else:
            ass_path = path2save  # type: ignore
            ass_path.mkdir(parents=True, exist_ok=True)

        # If there is more then one language, on the file name, it will add
        # what language is in converted  ass file.
        # e.g test-kor.ass and test-jp.ass
        lang_keys: list[str] = list(self.ass_lines.keys())
        if len(lang_keys) == 1:
            ass_path = ass_path.joinpath(f"{self.path2smi.stem}.ass")
            save_internal(ass_path, self.ass_lines[lang_keys[0]])
        else:
            for tmp_key in lang_keys:
                ass_path = ass_path.joinpath(
                    f"{self.path2smi.stem}-{tmp_key.upper()}.ass"
                )
                save_internal(ass_path, self.ass_lines[tmp_key])

        # Added message to notify where file has been saved
        print(f"Converted file has been saved as... \n{ass_path}")


def rgb2bgr(rgb: str) -> str:
    """Converting hex rgb color code to hex bgr color code.
    based on ASS specs (http://www.tcax.org/docs/ass-specs.htm), font color
    should given as long integer BGR (blue-green-red)  value.

    Args:
        rgb (str): Hex color code input

    Returns:
        str: Converted color code in BGR in hex
    """

    return rgb[4:6] + rgb[2:4] + rgb[0:2]


def save_internal(save_path: Path, lines: list[str]):
    """Helper function to combine save operation. Just try to be lazy

    Args:
        save_path (Path): Output path
        lines (list[str]): Data that try to write into drive
    """

    with open(save_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
