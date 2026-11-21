"""App mode: this engine belongs to the Mac app, which sets ANYSCRIBE_APP=1 when it starts it.

The only place that reads the variable; callers ask ``is_app()``.
"""

from __future__ import annotations

import os

APP_UPDATE_MESSAGE = "This anyscribe came with the Mac app, which updates itself."


def is_app() -> bool:
    return os.environ.get("ANYSCRIBE_APP") == "1"
