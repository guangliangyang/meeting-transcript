"""Replay a transcript from a file, for testing without audio or a meeting.

Enabled by setting MEETING_ASSISTANT_FAKE_TRANSCRIPT to a text file path.
Emits the same "[HH:MM:SS] text" shape as the real transcribers.
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from transcription.base import BaseTranscriber


class FakeTranscriber(BaseTranscriber):
    """Feeds lines from a file on a timer through the real callback path."""

    def __init__(self, on_transcript: Optional[Callable[[str], None]] = None,
                 source: Optional[Path] = None, interval: float = 2.0):
        super().__init__(on_transcript)
        self._source = Path(source) if source else None
        self._interval = interval
        self._transcript_parts: list[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _lines(self) -> list[str]:
        if not self._source or not self._source.exists():
            return []
        text = self._source.read_text(encoding="utf-8")
        return [l.strip() for l in text.splitlines() if l.strip()]

    def _replay(self) -> None:
        for line in self._lines():
            if not self._running:
                return
            entry = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
            with self._lock:
                self._transcript_parts.append(entry)
            if self.on_transcript:
                self.on_transcript(entry)
            time.sleep(self._interval)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        print("=" * 60)
        print(f"Replaying fake transcript from {self._source}")
        print("=" * 60)
        self._thread = threading.Thread(target=self._replay, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def get_full_transcript(self) -> str:
        with self._lock:
            return "\n".join(self._transcript_parts)

    def get_recent_transcript(self, last_n: int = 10) -> str:
        with self._lock:
            return "\n".join(self._transcript_parts[-last_n:])

    def clear(self) -> None:
        with self._lock:
            self._transcript_parts.clear()
