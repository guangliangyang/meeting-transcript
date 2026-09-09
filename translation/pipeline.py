"""Background translation pipeline.

Transcript lines arrive on the caption polling thread, which must never block:
a blocking HTTP call there delays polling and can make the Live Captions
overlap matching miss content. So submit() only enqueues, worker threads do the
network calls, and a single emitter thread prints, which is what keeps output in
submit order even though translations complete out of order.
"""

import queue
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from translation.provider import TranslationProvider

# "[HH:MM:SS] " - displayed, but not sent to the translator.
_TIMESTAMP = re.compile(r'^\[\d{2}:\d{2}:\d{2}\]\s*')

# (original, translation); translation is "" when unavailable.
OnPair = Callable[[str, str], None]


@dataclass
class _Segment:
    original: str
    payload: str
    deadline: float
    done: threading.Event = field(default_factory=threading.Event)
    translation: str = ""


class TranslationPipeline:
    """Translates transcript lines without delaying transcription."""

    def __init__(
        self,
        translator: Optional[TranslationProvider],
        on_pair: OnPair,
        workers: int = 1,
        queue_size: int = 32,
        max_hold_seconds: float = 3.0,
        min_chars: int = 3,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self._translator = translator
        self._on_pair = on_pair
        self._workers = max(1, workers)
        self._max_hold = max_hold_seconds
        self._min_chars = min_chars
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds

        self._work_q: queue.Queue = queue.Queue(maxsize=queue_size)
        # Unbounded: it only ever holds what _work_q holds plus what is in flight.
        self._order_q: queue.Queue = queue.Queue()

        self._threads: list[threading.Thread] = []
        self._running = False
        self._stopped = False

        self._breaker_lock = threading.Lock()
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    @property
    def enabled(self) -> bool:
        """True when translation will actually be attempted."""
        return self._translator is not None

    def start(self) -> None:
        """Start worker and emitter threads. No-op in passthrough mode."""
        if not self.enabled or self._running:
            return
        self._running = True

        for i in range(self._workers):
            t = threading.Thread(
                target=self._worker_loop, name=f"translate-{i}", daemon=True
            )
            t.start()
            self._threads.append(t)

        self._emitter = threading.Thread(
            target=self._emit_loop, name="translate-emit", daemon=True
        )
        self._emitter.start()

    def submit(self, text: str) -> None:
        """Queue a transcript line. Non-blocking; safe from any thread."""
        if not self.enabled or not self._running:
            # Passthrough: behave exactly as the app did before translation.
            self._on_pair(text, "")
            return

        payload = _TIMESTAMP.sub('', text).strip()
        segment = _Segment(
            original=text,
            payload=payload,
            deadline=time.monotonic() + self._max_hold,
        )

        # Ordering is fixed here, before any translation is attempted.
        self._order_q.put(segment)

        if len(payload) < self._min_chars or self._breaker_is_open():
            segment.done.set()
            return

        try:
            self._work_q.put_nowait(segment)
        except queue.Full:
            # Backlog: show the original immediately rather than growing memory.
            segment.done.set()

    def stop(self, timeout: float = 5.0) -> None:
        """Drain and shut down. Idempotent."""
        if self._stopped:
            return
        self._stopped = True
        if not self._running:
            return
        self._running = False

        deadline = time.monotonic() + timeout

        # Sentinels go in behind everything already queued, so workers finish the
        # real backlog first.
        for _ in self._threads:
            self._work_q.put(None)
        for t in self._threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))

        self._order_q.put(None)
        self._emitter.join(timeout=max(0.0, deadline - time.monotonic()))

    def _worker_loop(self) -> None:
        while True:
            segment = self._work_q.get()
            if segment is None:
                return
            try:
                # A backlog that drained past its deadline is discarded here, so
                # 32 stale segments cost microseconds rather than 32 x max_hold.
                if time.monotonic() >= segment.deadline:
                    continue
                try:
                    segment.translation = self._translator.translate(segment.payload)
                    self._note_success()
                except Exception:
                    self._note_failure()
            finally:
                segment.done.set()

    def _emit_loop(self) -> None:
        while True:
            segment = self._order_q.get()
            if segment is None:
                return
            # FIFO by submit order, and only this thread prints, so output order
            # is submit order no matter how the workers interleave.
            segment.done.wait(timeout=max(0.0, segment.deadline - time.monotonic()))
            try:
                self._on_pair(segment.original, segment.translation)
            except Exception:
                # Never let a display error kill the meeting.
                pass

    def _breaker_is_open(self) -> bool:
        """True while we are backing off after repeated failures.

        Without this, an offline network costs every line the full hold, forever.
        """
        with self._breaker_lock:
            if self._breaker_open_until == 0.0:
                return False
            if time.monotonic() < self._breaker_open_until:
                return True
            # Half-open: let one segment through to probe.
            self._breaker_open_until = 0.0
            return False

    def _note_success(self) -> None:
        with self._breaker_lock:
            self._consecutive_failures = 0
            self._breaker_open_until = 0.0

    def _note_failure(self) -> None:
        with self._breaker_lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._breaker_open_until = time.monotonic() + self._cooldown
