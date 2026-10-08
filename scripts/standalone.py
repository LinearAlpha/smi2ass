"""Nuitka entry point; install the project before compiling."""
from smi2ass.__main__ import main

# Compile the installed CLI entry point so packaged and native argument handling agree.
if __name__ == "__main__":
    main()
