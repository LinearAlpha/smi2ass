# Built in modules
import argparse
from pathlib import Path

# Custom made modules
if __package__:
    from . import __version__
    from .smi2ass import smi2ass
else:
    from smi2ass import smi2ass
    __version__ = "1.5.1"


def cmd_arg() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smi2ass",
        description="Converting SAMI (SMI) into Advanced SubStation Alpha (ASS) subtitle",
    )

    parser.add_argument("--version", action="version", version=f"smi2ass {__version__}")
    parser.add_argument("--settings-dir", default="", help="Directory containing custom settings JSON files")

    parser.add_argument(
        "file_name",
        metavar="File_Name",
        type=str,
        nargs="+",
        help="SMI file name to  be processed",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output_dir",
        type=str,
        default=str(Path().cwd().joinpath("out")),
        help="The output folder where file will be saved",
    )

    parser.add_argument(
        "-t",
        "--title",
        type=str,
        help="Tile of the video file for subtitle header",
    )

    parser.add_argument("-f", "--font", type=str, help="Font of the subtitle")

    parser.add_argument(
        "-s", "--font_size", type=int, help="Font size of subtitle"
    )

    parser.add_argument(
        "-res_x",
        "--resolution_x",
        type=int,
        help="Horizontal resolution of the video",
    )

    parser.add_argument(
        "-res_y",
        "--resolution_y",
        type=int,
        help="Vertical resolution of the video",
    )

    parser.add_argument(
        "--add_time",
        type=int,
        help="Time in millisecond to add on subtitle",
    )

    parser.add_argument(
        "--sub_time",
        type=int,
        help="Time in millisecond to subtract on subtitle",
    )

    return parser


def update_style(obj: smi2ass, args: argparse.Namespace) -> None:
    """Updating ASS header style based on the user inputs

    Args:
        obj (smi2ass): smi2ass class object, if I'm right since this is objec,
        it will be pass bt reference
        args (argparse.Namespace): Input arguments
    """

    # It removes first character of the string
    remove_first_char = lambda s: s[:0] + "" + s[1:]

    # In case when there is white space in the front of string, it causes when
    # program is making new directory for converted output. Thus, it need to
    # remove it
    if args.output_dir[0] == " ":
        args.output_dir = remove_first_char(args.output_dir)

    if args.title != None:  # Update title
        obj.update_title(args.title)

    if args.font != None:  # Update font
        # To prevent error when it is playing on the video player
        if args.font[0] == " ":
            args.font = remove_first_char(args.font)
        obj.update_font_name(args.font)

    if args.font_size != None:  # update font size
        obj.update_font_size(args.font_size)

    # Updating resolution
    if (args.resolution_x != None) and (args.resolution_y != None):
        obj.update_res(res_x=args.resolution_x, res_y=args.resolution_y)
    elif (args.resolution_x != None and args.resolution_y == None) or (
        args.resolution_x == None and args.resolution_y != None
    ):
        msg_str: str
        if args.resolution_x != None:
            msg_str = "resolution_x"
        else:
            msg_str = "resolution_y"
        print(
            f'Cannot update resolution, you only entered "{msg_str}."'
            + "Both resolutions are needed"
        )


def main() -> None:
    parser: argparse.ArgumentParser = cmd_arg()
    args: argparse.Namespace = parser.parse_args()

    obj_smi2ass = smi2ass(setting_path=args.settings_dir)
    update_style(obj_smi2ass, args)

    # Check if user gave time offset
    if args.add_time != None or args.sub_time != None:
        time_offset: int
        if args.add_time != None:
            time_offset = args.add_time
        else:
            time_offset = args.sub_time * -1

        # Update time offset
        obj_smi2ass.set_time_offset(time_offset)

    for tmp_file_name in args.file_name:
        obj_smi2ass.to_ass(tmp_file_name).save(args.output_dir)


if __name__ == "__main__":
    main()
