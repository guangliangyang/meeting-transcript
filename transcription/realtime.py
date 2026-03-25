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

        # Track captions
        self._last_output_caption = ""  # Caption at last output
        self._current_caption = ""  # Current full caption
        self._last_output_time = 0
        self._output_interval = 10  # Output every 10 seconds
        self._poll_interval = 0.5

    def _find_captions_window(self):
        """Find the Windows Live Captions window."""
        try:
            desktop = Desktop(backend="uia")
            # Try to find by title
            windows = desktop.windows(title_re=".*Live captions.*|.*Captions.*")
            if windows:
                return windows[0]
            # Fallback search
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
        """Extract the main caption text from the window.

        Tries to find the Text control that contains the actual captions.
        """
        try:
            best_text = ""

            # Look for Text controls (these typically hold the caption content)
            for child in window.descendants():
                try:
                    # Get control type
                    ctrl_type = child.element_info.control_type
                    text = child.window_text()

                    if not text or len(text) < 10:
                        continue

                    # Skip UI elements
                    text_lower = text.lower().strip()
                    if text_lower in {'settings', 'close', 'minimize', 'maximize',
                                      'live captions', ''}:
                        continue
                    if text_lower.startswith('ready to show'):
                        continue
                    if text_lower.startswith('getting ready'):
                        continue
                    if text_lower.startswith('taking a little'):
                        continue

                    # Prefer Text controls, but accept others
                    # Take the longest text found
                    if len(text) > len(best_text):
                        best_text = text.strip()

                except Exception:
                    pass

            return best_text
        except Exception:
            return ""

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
                current_caption = self._get_caption_text(window)

                if current_caption:
                    self._current_caption = current_caption

                # Check if it's time to output (every 10 seconds)
                current_time = time.time()
                if current_time - self._last_output_time >= self._output_interval:
                    self._flush_new_text()
                    self._last_output_time = current_time

            except ElementNotFoundError:
                window = None
            except Exception as e:
                print(f"[DEBUG] Error: {e}")
                window = None

            time.sleep(self._poll_interval)

    def _flush_new_text(self) -> None:
        """Output new text since last output."""
        if not self._current_caption:
            return

        curr = self._current_caption
        last = self._last_output_caption

        if not last:
            # First output - use all current text
            new_text = curr
        else:
            # Find the longest common prefix (fuzzy - ignore minor differences)
            new_text = self._find_new_portion(last, curr)

        if new_text and len(new_text) > 5:
            timestamp = datetime.now().strftime("%H:%M:%S")
            transcript_entry = f"[{timestamp}] {new_text}"

            with self._lock:
                self._transcript_parts.append(transcript_entry)

            if self.on_transcript:
                self.on_transcript(transcript_entry)

        # Update last output caption
        self._last_output_caption = self._current_caption

    def _find_new_portion(self, last: str, curr: str) -> str:
        """Find new portion by matching words, not exact characters."""
        if len(curr) <= len(last):
            return ""

        # Split into words for fuzzy matching
        last_words = last.lower().split()
        curr_words = curr.lower().split()

        if not last_words:
            return curr

        # Find where last text ends in current (by word matching)
        # Look for a sequence of last words in curr words
        last_len = len(last_words)

        # Try to find the last few words of 'last' in 'curr'
        # Start from the end of 'last' and look for matches
        match_start = -1
        for i in range(len(curr_words) - 3):
            # Check if a sequence of words matches the end of last
            if curr_words[i:i+min(5, last_len)] == last_words[-min(5, last_len):]:
                match_start = i + min(5, last_len)
                break

        if match_start > 0 and match_start < len(curr_words):
            # Return words after the match point
            # Reconstruct from original curr (preserve case/punctuation)
            # Find approximate character position
            word_count = 0
            char_pos = 0
            for i, char in enumerate(curr):
                if char == ' ':
                    word_count += 1
                    if word_count >= match_start:
                        char_pos = i + 1
                        break

            return curr[char_pos:].strip() if char_pos > 0 else ""

        # Fallback: use character length approximation
        # Take everything after the length of last text
        if len(curr) > len(last) + 10:
            return curr[len(last):].strip()

        return ""

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
        self._last_output_caption = ""
        self._current_caption = ""

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
        self._flush_new_text()
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
        self._last_output_caption = ""
        self._current_caption = ""

    def save_transcript(self, filepath: str) -> None:
        """Save transcript to a file."""
        with self._lock:
            transcript = "\n".join(self._transcript_parts)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
