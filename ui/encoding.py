"""Console encoding setup.

Chinese cannot be written to a default Windows console: stdout is cp1252 and the
console code page is 437, so any CJK character raises UnicodeEncodeError. Rich
fails exactly like plain print here, so this is not a cosmetic concern - it has
to run before anything tries to display a translation.
"""

import ctypes
import sys

_CP_UTF8 = 65001

_done = False


def enable_utf8_console() -> None:
    """Make stdout/stderr able to emit CJK. Idempotent, never raises."""
    global _done
    if _done:
        return
    _done = True

    if sys.platform == "win32":
        try:
            # Output code page only. Setting the *input* code page to 65001 is the
            # well-known cmd.exe breakage; we read no stdin (keyboard.wait() is a
            # hook, not a read), so there is nothing to gain from it.
            ctypes.windll.kernel32.SetConsoleOutputCP(_CP_UTF8)
        except Exception:
            pass

    for stream in (sys.stdout, sys.stderr):
        # PyInstaller windowed mode leaves these as None.
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            # errors="replace" is the never-crash guarantee: a stray character
            # degrades to "?" instead of killing the caption poll thread through
            # the transcript callback chain.
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
