"""Lazy entry point so a CLI-only installation can explain the GUI extra."""
import argparse
from pathlib import Path
import sys

from . import __version__


def main(argv=None):
    """Parse launch options, load optional Qt, and start the desktop event loop."""
    parser = argparse.ArgumentParser(description="smi2ass desktop subtitle converter")
    parser.add_argument("files", nargs="*", help="SAMI files to add to the conversion queue")
    parser.add_argument("--version", action="version", version=f"smi2ass GUI {__version__}")
    parser.add_argument("--smoke-test", metavar="REPORT", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    # Parse --version before importing Qt so CLI-only installations can still report it.
    try:
        from PySide6.QtWidgets import QApplication
        from .gui import MainWindow, apply_theme
    except ImportError as error:
        if isinstance(error, ModuleNotFoundError) and (error.name or "").startswith("PySide6"):
            print('The GUI requires Qt. Install it with: python -m pip install "smi2ass[gui]"', file=sys.stderr)
        else:
            print("Could not load the desktop interface. See the GUI prerequisites in README.md.", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1
    app = QApplication([sys.argv[0]])
    app.setApplicationName("smi2ass")
    app.setOrganizationName("LinearAlpha")
    apply_theme(app)
    if args.smoke_test:
        from .gui_smoke import run_smoke
        return run_smoke(app, Path(args.smoke_test))
    window = MainWindow()
    window.show()
    if args.files:
        window.add_paths(args.files)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
