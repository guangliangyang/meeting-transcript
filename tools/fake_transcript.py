"""Drive the real display path with canned transcript lines. No audio needed.

Usage:
    python tools/fake_transcript.py [--offline] [--slow N] [--burst] [--advice]
"""

import argparse
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.factory import get_translator, describe_translator  # noqa: E402
from translation.pipeline import TranslationPipeline  # noqa: E402
from translation.provider import TranslationProvider  # noqa: E402
from ui.console import ConsoleUI  # noqa: E402
from ui.encoding import enable_utf8_console  # noqa: E402

LINES = [
    "Morning everyone, let's start.",
    "The entitlement service needs a new column on the subscription table, "
    "which means a liquibase changeset and a datastore version bump.",
    "We should return list[str] here, not a raw dict[str, int] - and the "
    "[inaudible] part of the config is still wrong.",
    "so I think we just keep polling until the window shows up and then we "
    "read whatever the longest text node happens to be at that moment",
    ("The consul configuration is still not refreshing at runtime because the "
     "service injects IOptions instead of IOptionsSnapshot, and that means "
     "every value is read once at startup and then cached forever, so a change "
     "in the key value store never reaches the running container until it is "
     "restarted, which defeats the entire point of centralising the config. "
     "We should fix that before we cut the release tag, otherwise the ops team "
     "will keep filing the same ticket every sprint and we will keep telling "
     "them to restart the service by hand, which is not a real answer. " * 2),
    "Ray will review the merge request tomorrow.",
]


class _Failing(TranslationProvider):
    def translate(self, text: str) -> str:
        raise RuntimeError("simulated network failure")


class _Slow(TranslationProvider):
    def __init__(self, inner, delay):
        self._inner, self._delay = inner, delay

    def translate(self, text: str) -> str:
        time.sleep(self._delay)
        return self._inner.translate(text)


def stamp(text):
    return f"[{datetime.now().strftime('%H:%M:%S')}] {text}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--slow", type=float, default=0)
    ap.add_argument("--burst", action="store_true")
    ap.add_argument("--advice", action="store_true")
    args = ap.parse_args()

    enable_utf8_console()
    ui = ConsoleUI()

    translator = get_translator()
    if args.offline:
        translator = _Failing()
    elif args.slow:
        translator = _Slow(translator, args.slow)

    pipe = TranslationPipeline(translator, ui.add_transcript_pair)
    pipe.start()
    ui.show_translation_status(pipe.enabled, describe_translator(translator))

    started = time.monotonic()

    if args.advice:
        def spam():
            for _ in range(4):
                time.sleep(0.7)
                ui.show_advice("**Advice panel** printed from another thread.")
        threading.Thread(target=spam, daemon=True).start()

    if args.burst:
        for i in range(100):
            pipe.submit(stamp(f"Burst line number {i:03d} about the release."))
    else:
        for line in LINES:
            pipe.submit(stamp(line))
            time.sleep(1.0)
        # Two lines 50ms apart - pairs must not interleave.
        pipe.submit(stamp("Rapid line one, does it interleave?"))
        time.sleep(0.05)
        pipe.submit(stamp("Rapid line two, right behind it."))

    pipe.stop(timeout=15.0)
    elapsed = time.monotonic() - started
    ui.print(f"\n[dim]total wall time {elapsed:.1f}s[/dim]")


if __name__ == "__main__":
    main()
