"""Separate GUI entry point for Nuitka's desktop executable."""
from smi2ass.gui_launcher import main

# Propagate startup/smoke-test failures to CI even when Windows hides the GUI console.
if __name__ == "__main__":
    raise SystemExit(main())
