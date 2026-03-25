"""Real-time transcription using Windows Live Captions."""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


class RealtimeTranscriber:
    """Captures transcription from Windows Live Captions."""

    def __init__(self, on_transcript: Optional[Callable[[str], None]] = None):
        if not HAS_PYWINAUTO:
            raise ImportError("pywinauto is required")

        self.on_transcript = on_transcript
        self._transcript_parts: list[str] = []
        self._lock = threading.Lock()
        self._running = False

        # Our own buffer - captures continuously, never loses content
        self._full_transcript = ""
        self._last_seen_text = ""  # Last text seen in Live Captions window
        self._last_output_position = 0  # Position in _full_transcript at last output

        self._last_output_time = 0
        self._output_interval = 10  # Output every 10 seconds
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

                # Output every 10 seconds from OUR buffer
                current_time = time.time()
                if current_time - self._last_output_time >= self._output_interval:
                    self._output_from_buffer()
                    self._last_output_time = current_time

            except ElementNotFoundError:
                window = None
            except Exception as e:
                print(f"[DEBUG] Error: {e}")
                window = None

            time.sleep(self._poll_interval)

    def _output_from_buffer(self) -> None:
        """Output new content from our buffer since last output."""
        new_text = self._full_transcript[self._last_output_position:].strip()

        if new_text and len(new_text) > 3:
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcript_entry = f"[{timestamp}] {new_text}"

            with self._lock:
                self._transcript_parts.append(transcript_entry)

            if self.on_transcript:
                self.on_transcript(transcript_entry)

        # Update position for next output
        self._last_output_position = len(self._full_transcript)

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
        print(f"Transcript output interval: {self._output_interval} seconds")
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
