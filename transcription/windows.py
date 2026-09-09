"""Real-time transcription using Windows Live Captions."""

import re
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from config import (
    TRANSCRIPT_MAX_FLUSH_SECONDS,
    TRANSCRIPT_MAX_PENDING_WORDS,
    TRANSCRIPT_MIN_FLUSH_CHARS,
    TRANSCRIPT_MIN_FLUSH_SECONDS,
)
from transcription.base import BaseTranscriber

# A terminator followed by whitespace or the end of the buffer. Abbreviations
# ("e.g.") false-trigger; the cost is one short line, which is not worth an
# abbreviation list.
_SENTENCE_END = re.compile(r"""[.!?](?:["')\]]+)?(?=\s|$)""")

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


class WindowsTranscriber(BaseTranscriber):
    """Captures transcription from Windows Live Captions."""

    def __init__(self, on_transcript: Optional[Callable[[str], None]] = None):
        super().__init__(on_transcript)

        if not HAS_PYWINAUTO:
            raise ImportError("pywinauto is required for Windows transcription")

        self._transcript_parts: list[str] = []
        self._lock = threading.Lock()
        self._running = False

        # Our own buffer - captures continuously, never loses content
        self._full_transcript = ""
        self._last_seen_text = ""  # Last text seen in Live Captions window
        self._last_output_position = 0  # Position in _full_transcript at last output

        self._last_output_time = 0
        # Flush on sentence boundaries between a floor and a cap, so translated
        # lines appear every few seconds instead of every ten.
        self._output_min_interval = TRANSCRIPT_MIN_FLUSH_SECONDS
        self._output_max_interval = TRANSCRIPT_MAX_FLUSH_SECONDS
        self._output_min_chars = TRANSCRIPT_MIN_FLUSH_CHARS
        self._output_max_words = TRANSCRIPT_MAX_PENDING_WORDS
        # Serialises _output_from_buffer: stop() calls it from the hotkey thread
        # while the poll thread may already be inside it.
        self._output_lock = threading.Lock()
        # Walking the UIA tree is the expensive part - capture and output are
        # deliberately decoupled, so do not lower this to speed up output.
        self._poll_interval = 0.5

    def _find_captions_window(self):
        """Find the Windows Live Captions window."""
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows(title_re=".*Live captions.*|.*Captions.*")
            if windows:
                return windows[0]
            for win in desktop.windows():
                try:
                    if "caption" in win.window_text().lower():
                        return win
                except:
                    pass
        except Exception:
            pass
        return None

    def _get_caption_text(self, window) -> str:
        """Extract the main caption text from the window."""
        try:
            best_text = ""
            skip_phrases = {'settings', 'close', 'minimize', 'maximize', 'live captions', ''}

            for child in window.descendants():
                try:
                    text = child.window_text()
                    if not text or len(text) < 10:
                        continue

                    text_lower = text.lower().strip()
                    if text_lower in skip_phrases:
                        continue
                    if text_lower.startswith('ready to show'):
                        continue
                    if text_lower.startswith('getting ready'):
                        continue
                    if text_lower.startswith('taking a little'):
                        continue

                    # Take the longest text found
                    if len(text) > len(best_text):
                        best_text = text.strip()
                except Exception:
                    pass

            return best_text
        except Exception:
            return ""

    def _normalize_word(self, word: str) -> str:
        """Remove punctuation from word for comparison."""
        return ''.join(c for c in word.lower() if c.isalnum())

    def _extract_new_content(self, current_text: str) -> str:
        """Extract content that's new since last seen window text.

        Compare against last_seen_text (what was in window before).
        Handles Live Captions' sliding window and punctuation changes.
        """
        curr = current_text.strip()

        if not self._last_seen_text:
            return curr

        last = self._last_seen_text

        # Normalize for comparison (remove punctuation effects)
        curr_normalized = ' '.join(self._normalize_word(w) for w in curr.split())
        last_normalized = ' '.join(self._normalize_word(w) for w in last.split())

        # Case 1: Current extends last (new text appended)
        if curr_normalized.startswith(last_normalized):
            # Find where last ends in original curr
            last_word_count = len(last.split())
            curr_words = curr.split()
            if last_word_count < len(curr_words):
                return " ".join(curr_words[last_word_count:])
            return ""

        # Case 2: Sliding window - find overlap using normalized words
        curr_words = curr.split()
        last_words = last.split()

        if len(curr_words) < 3 or len(last_words) < 3:
            return curr

        # Normalize words for matching
        last_norm = [self._normalize_word(w) for w in last_words]
        curr_norm = [self._normalize_word(w) for w in curr_words]

        # Find where last words end and current continues
        for seq_len in range(min(10, len(last_words)), 2, -1):
            search_seq = last_norm[-seq_len:]

            for i in range(len(curr_norm) - seq_len + 1):
                if curr_norm[i:i+seq_len] == search_seq:
                    new_start = i + seq_len
                    if new_start < len(curr_words):
                        return " ".join(curr_words[new_start:])
                    return ""

        # No overlap found - this might be after a long pause
        # Return all if it seems like genuinely new content
        return curr

    def _poll_captions(self) -> None:
        """Poll the Live Captions window for new text."""
        window = None
        retry_count = 0
        self._last_output_time = time.time()

        while self._running:
            try:
                if window is None:
                    window = self._find_captions_window()
                    if window is None:
                        retry_count += 1
                        if retry_count % 10 == 1:
                            print("[INFO] Waiting for Live Captions window...")
                            print("       Press Win+Ctrl+L to open Live Captions")
                        time.sleep(self._poll_interval)
                        continue
                    else:
                        print("[INFO] Found Live Captions window!")
                        retry_count = 0

                # Get current caption text
                current_text = self._get_caption_text(window)

                # Capture new content IMMEDIATELY (don't wait for output interval)
                if current_text and current_text != self._last_seen_text:
                    new_content = self._extract_new_content(current_text)
                    if new_content and len(new_content) > 1:
                        # Append to our buffer immediately
                        self._full_transcript += " " + new_content
                    self._last_seen_text = current_text

                # Output from OUR buffer, preferring sentence boundaries
                current_time = time.time()
                elapsed = current_time - self._last_output_time
                if elapsed >= self._output_max_interval:
                    self._output_from_buffer()
                    self._last_output_time = current_time
                elif elapsed >= self._output_min_interval:
                    pending = self._full_transcript[self._last_output_position:]
                    if len(pending.strip()) >= self._output_min_chars:
                        cut = self._find_flush_boundary(pending)
                        if cut:
                            self._output_from_buffer(limit=cut)
                            self._last_output_time = current_time

            except ElementNotFoundError:
                window = None
            except Exception as e:
                print(f"[DEBUG] Error: {e}")
                window = None

            time.sleep(self._poll_interval)

    def _find_flush_boundary(self, pending: str) -> int:
        """Length of `pending` that ends on a sentence, or 0 to keep buffering.

        Live Captions can be configured with punctuation off, in which case no
        terminator ever appears - hence the word-count fallback.
        """
        last = None
        for match in _SENTENCE_END.finditer(pending):
            last = match

        if last is not None:
            end = last.end()
            # Absorb the following space so it does not lead the next segment.
            while end < len(pending) and pending[end].isspace():
                end += 1
            return end

        if len(pending.split()) >= self._output_max_words:
            cut = pending.rfind(" ")
            if cut > 0:
                return cut + 1

        return 0

    def _output_from_buffer(self, limit: Optional[int] = None) -> None:
        """Output buffered content.

        `limit` is a length relative to the current output position; None means
        everything buffered so far.
        """
        with self._output_lock:
            start = self._last_output_position
            total = len(self._full_transcript)
            end = total if limit is None else min(start + limit, total)

            new_text = self._full_transcript[start:end].strip()

            # Advance unconditionally: short fragments are noise and are meant to
            # be discarded. `_full_transcript` is append-only, so these indices
            # stay valid - if it ever gains trimming, decrement this by the same
            # amount.
            self._last_output_position = end

            transcript_entry = None
            if new_text and len(new_text) > 3:
                timestamp = datetime.now().strftime("%H:%M:%S")
                transcript_entry = f"[{timestamp}] {new_text}"

                with self._lock:
                    self._transcript_parts.append(transcript_entry)

        # Callback outside both locks - it must not run with a lock held.
        if transcript_entry and self.on_transcript:
            self.on_transcript(transcript_entry)

    def _open_live_captions(self) -> None:
        """Auto-open Windows Live Captions."""
        try:
            import keyboard
            print("[INFO] Opening Windows Live Captions (Win+Ctrl+L)...")
            keyboard.press_and_release('win+ctrl+l')
            time.sleep(2)
        except Exception as e:
            print(f"[WARN] Could not auto-open: {e}")
            print("       Please open manually: Win+Ctrl+L")

    def start(self) -> None:
        """Start capturing from Live Captions."""
        if self._running:
            return

        self._running = True
        self._full_transcript = ""
        self._last_seen_text = ""
        self._last_output_position = 0

        print("=" * 60)
        print("Starting Windows Live Captions capture...")
        print(
            f"Transcript flush: {self._output_min_interval}-"
            f"{self._output_max_interval}s, on sentence boundaries"
        )
        print("=" * 60)

        self._open_live_captions()

        self._poll_thread = threading.Thread(target=self._poll_captions, daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        """Stop capturing."""
        # Flush any remaining text
        self._output_from_buffer()
        self._running = False

    def get_full_transcript(self) -> str:
        """Get the complete transcript."""
        with self._lock:
            return "\n".join(self._transcript_parts)

    def get_recent_transcript(self, last_n: int = 10) -> str:
        """Get the last N transcript entries."""
        with self._lock:
            return "\n".join(self._transcript_parts[-last_n:])

    def clear(self) -> None:
        """Clear all transcript data."""
        with self._lock:
            self._transcript_parts.clear()
        self._full_transcript = ""
        self._last_seen_text = ""
        self._last_output_position = 0

    def save_transcript(self, filepath: str) -> None:
        """Save transcript to a file."""
        with self._lock:
            transcript = "\n".join(self._transcript_parts)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
