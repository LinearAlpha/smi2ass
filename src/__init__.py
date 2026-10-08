"""Public conversion API and release version shared by CLI and GUI launchers."""

# Keep the historical imports available to scripts using ``from smi2ass import ...``.
from . import ass_settings
from .ass_settings import AssStyle
from . import smi2ass
from .smi2ass import smi2ass
from .smi2ass import rgb2bgr

__version__ = "1.5.1"
