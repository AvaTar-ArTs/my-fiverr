"""Private, local-first Fiverr Seller OS."""

import os
from pathlib import Path
import sys

__version__ = "0.1.0"


def state_path() -> Path:
    """Return the state location without creating or modifying it.

    ``FIVERR_SELLER_OS_STATE_DIR`` may point to any filesystem path owned by
    the user. On macOS, the default follows the platform's Application Support
    convention. Other platforms use the XDG local data location when supplied,
    or a ``~/.local/share`` fallback.
    """
    configured_path = os.environ.get("FIVERR_SELLER_OS_STATE_DIR")
    if configured_path is not None:
        if not configured_path.strip():
            raise ValueError("FIVERR_SELLER_OS_STATE_DIR must be a non-empty path")
        return Path(configured_path).expanduser()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "FiverrSellerOS"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "FiverrSellerOS"
    return Path.home() / ".local" / "share" / "FiverrSellerOS"
