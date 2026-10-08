"""Parse SAMI cues into language tracks and convert inline markup to ASS events."""

import re
from typing import Self
from collections import defaultdict
from operator import itemgetter
from pathlib import Path
import html

# PIP installed modules
import charset_normalizer
from bs4 import BeautifulSoup as bs
from bs4 import ResultSet

# Custom modules
if __package__:
    from .ass_settings import AssStyle
else:  # Retain direct source execution.
    from ass_settings import AssStyle


class smi2ass(AssStyle):
    """Reuse style/offset settings across inputs while keeping each file's cues separate."""

    def __init__(self, smi_path: str = "", **kwargs) -> None:
        """Load settings immediately and optionally preprocess an initial SAMI file."""

        # Initializing parent class
        super().__init__(**kwargs)

        self.path2smi: Path  # Path to SMI file
        self.smi_sgml: str
        self.smi_sgml_bs: ResultSet
        # Each language maps to [BeautifulSoup sync block, ASS timestamp, milliseconds] rows.
        self.smi_lines: dict[str, list[any]] = defaultdict(list)
        # Each output track contains its header followed by complete Dialogue records.
        self.ass_lines: dict[str, list[str]] = defaultdict(list)
        # Flag initialization process is complete before converting to ASS
        self.flag_preprocess: bool = False

        # Setting time offset from original file
        self.flag_time_offset: bool = False
        self.time_offset: int = 0

        # Delayed preprocessing lets callers set style and offset before reading cues.
        if smi_path != "":
            self.__preprocess(smi_path)

    def __preprocess(self, smi_file_input: str) -> None:
        """Reset per-file state, decode input, and extract language/timestamp groups."""

        self.path2smi = Path(smi_file_input)  # Saving input path
        # A reused converter must not carry languages or output text from the previous file.
        self.flag_preprocess = False
        self.smi_lines.clear()
        self.ass_lines.clear()

        # Printing which file is currently converting
        self.log(f"\nConverting... \n{self.path2smi}")

        # Check if file is accessible. If it is not, program will raise error.
        try:
            # Detect from bytes before decoding legacy Korean and Unicode subtitle files.
            with open(smi_file_input, "rb") as f:
                f_encoding: str | None = charset_normalizer.detect(f.read())["encoding"]
            self.encoding = f_encoding
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

        # Keep sync blocks together so each language can derive cue ends from its next start.
        self.__time_lan()

        # Only mark ready after parsing and timestamp validation succeed.
        self.flag_preprocess = True

    def __convert_whitespace(self) -> None:
        """Legacy whitespace pass; its unassigned replacements currently leave text intact."""

        # TODO: assign str.replace results when deliberately changing normalization behavior.
        whitespace: list[str] = ["\u000D\u000A", "\u000A", "\u000D"]

        # CRLF, LF to a whitespace
        for temp in whitespace:
            self.smi_sgml.replace(temp, " ")

        # TAB to whitespace
        self.smi_sgml.replace("\t", "    ")

    def __convert_ss(self) -> None:
        """Protect spaces around markup with placeholders decoded after tag conversion."""

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

        # Legacy Unicode replacements are unassigned; only the regex passes below mutate text.
        for tmp_ss in char_ss:
            self.smi_sgml.replace(
                tmp_ss, f"smi2ass_unicode({str(ord(tmp_ss))})"
            )

        # Placeholders preserve ordinary spaces while BeautifulSoup replaces inline tags.
        self.smi_sgml = re.sub(r"> +<", ">smi2ass_unicode(32)<", self.smi_sgml)
        self.smi_sgml = re.sub(r"> +", ">smi2ass_unicode(32)", self.smi_sgml)
        self.smi_sgml = re.sub(r" +<", "smi2ass_unicode(32)<", self.smi_sgml)

        # Ruby annotations should not inherit padding from these placeholders.
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
        """Insert sync boundaries so SAMI's usually unclosed tags do not nest cues."""

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

        # Round before splitting units so 995 ms carries into the next second.
        centiseconds = round(ms / 10)
        hours, centiseconds = divmod(centiseconds, 360000)
        minutes, centiseconds = divmod(centiseconds, 6000)
        seconds, centiseconds = divmod(centiseconds, 100)
        return "%01d:%02d:%02d.%02d" % (hours, minutes, seconds, centiseconds)

    def __time_lan(self) -> None:
        """Group valid sync blocks by normalized language, applying offsets in milliseconds."""

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
                self.log(f"Failed to extract language class: {lines}")
                self.log('Language has been set to "UNKNOWNCC"')

            # -1 marks malformed/negative starts and must remain invalid after an offset.
            try:
                time_code = int(lines["start"])
                if time_code < 0:
                    time_code = -1
                    self.log(f"Negative time code: \n\n{lines}\n")
            except:
                time_code = -1
                self.log(f"Failed to extract time code: \n\n{lines}\n")

            # Adjust subtitle timecode based on the offset input
            # Zero is a valid cue start; invalid timestamps must not be revived by an offset.
            if self.flag_time_offset and time_code >= 0:
                time_code += self.time_offset

            # The key of the dictionary is language code in ass.
            # temporarily hols smi line data in to tmp_lines, and data
            # structure is [smi lines, ass time code, time in ms]
            if time_code >= 0:
                ass_lang_code: str = self.get_lang_code(lang_tag[0].upper())
                tmp_lines[ass_lang_code].append(
                    [lines, self.__ms2timestamp(time_code), time_code]
                )

        # Ascending cue counts put the shortest track first (also determines output order).
        tmp_lines = dict(
            sorted(tmp_lines.items(), key=lambda item: len(item[1]))
        )

        if not tmp_lines:
            raise ValueError("No valid subtitle cues found. Check the SAMI file and timing offset.")

        # Legacy imbalance check records [language, cue count, ratio to first track].
        # TODO: revisit this heuristic separately: the current baseline is the shortest track,
        # so nonempty groups cannot reach its <= 10% merge threshold.
        line_count: list[any] = []
        # Use the first (shortest) track as the existing ratio baseline.
        tmp_key: str = list(tmp_lines.keys())[0]
        for tmp_lang in tmp_lines.keys():
            tmp_len: int = len(tmp_lines[tmp_lang])
            line_count.append(
                [tmp_lang, tmp_len, tmp_len / len(tmp_lines[tmp_key])]
            )

        if len(line_count) != 1:
            for tmp in line_count:
                tmp_key: str = tmp[0]
                # Legacy merge branch for tracks at or below the baseline's 10% threshold.
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
        """Render one language track; inline tag replacement consumes its parsed blocks."""
        # Setting first item to be ASS style header
        tmp_ass_lines: list[str] = [self.ass_header()]

        for i in range(len(lines2conv)):
            # Getting current line of SMI
            tmp_line: bs = lines2conv[i][0]

            # Setting converted timecode
            track_start: str = lines2conv[i][1]  # Start time of subtitle

            # SAMI gives starts only: the next cue ends this one; the final cue gets one second.
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

            # Legacy annotation pass targets remaining <s> tags; this is not full ruby support.
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
                            self.log(f"Failed to convert color name: {smi_col}")

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

            # Decode both space placeholders and ordinary HTML character entities.
            contents = html.unescape(contents)

            # Removes next line character to avoid error when it sets loading
            contents = re.sub("\n", "", contents, len(contents) - 1)

            # Dialogue records must reference the selected style name in [V4+ Styles].
            # Blank sync blocks end the previous cue but do not create visible Dialogue rows.
            if len(contents.strip()) != 0:
                tmp_ass_lines.append(
                    "Dialogue: 0,%s,%s,%s,,0000,0000,0000,,%s\n"
                    % (track_start, track_end, self.ass_style["style"]["Name"], contents)
                )

        return tmp_ass_lines

    def update_file2conv(self, smi_path: str) -> Self:
        """Load a new input, retaining style/offset settings, and return self for chaining."""

        self.__preprocess(smi_path)

        return self

    def set_time_offset(self, offset: int) -> None:
        """Set a millisecond offset for subsequent preprocessing; negative values advance cues."""
        self.flag_time_offset = True
        self.time_offset = offset

    def to_ass(self, smi_path: str = "") -> Self:
        """Convert the loaded input or load a new path, then return self for save chaining."""

        # If there is path input then update to new SMI file
        if smi_path != "":
            self.update_file2conv(smi_path)

        # If class was not initialized print error message.
        if not self.flag_preprocess:
            self.log(
                "Initialization  process is not completed\n"
                + 'Please Initialize class by calling "update_file2conv" method'
            )
        else:
            for key, value in self.smi_lines.items():
                self.ass_lines[key] = self.__core(value)

        return self

    def save(self, path2save: str | Path = "") -> None:
        """Write UTF-8 tracks beside the source, or into an explicitly selected folder."""

        output_dir = self.path2smi.parent if path2save == "" else Path(path2save)
        output_dir.mkdir(parents=True, exist_ok=True)
        multiple_languages = len(self.ass_lines) > 1
        # Preserve plain names for one track; language suffixes distinguish multilingual output.
        for language, lines in self.ass_lines.items():
            suffix = f"-{language.upper()}" if multiple_languages else ""
            ass_path = output_dir / f"{self.path2smi.stem}{suffix}.ass"
            save_internal(ass_path, lines)
            self.log(f"Converted file has been saved as... {ass_path}")


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
    """Write already formatted ASS records as UTF-8 without adding extra separators."""

    with open(save_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

