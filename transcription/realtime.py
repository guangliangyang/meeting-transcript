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

        # Track the longest text seen - only output what extends beyond it
        self._longest_seen = ""
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
        except Exception as e:
            pass
        return None

    def _get_caption_text(self, window) -> str:
        """Extract text from the captions window."""
        try:
            # Skip UI elements
            skip = {'settings', 'close', 'minimize', 'maximize', 'live captions', ''}
            texts = []
            for child in window.descendants():
                try:
                    text = child.window_text()
                    if text and len(text) > 5 and text.lower().strip() not in skip:
                        texts.append(text.strip())
                except:
                    pass
            return texts  # Return list of all texts
        except:
            return []

    def _find_new_content(self, texts: list) -> str:
        """Find new content from the list of texts."""
        if not texts:
            return ""

        # Skip status messages
        skip_phrases = ['ready to show', 'getting ready', 'taking a little longer']
        seen_lower = self._longest_seen.lower() if self._longest_seen else ""

        # Look for text that EXTENDS our previous text (priority)
        best_extending = None
        best_new_part = ""

        for text in texts:
            text = text.strip()
            if len(text) < 20:
                continue
            if any(phrase in text.lower() for phrase in skip_phrases):
                continue

            text_lower = text.lower()

            # First time - take any text > 20 chars
            if not self._longest_seen:
                if best_extending is None or len(text) > len(best_extending):
                    best_extending = text
                continue

            # Look for text that CONTAINS our previous (it extended)
            if seen_lower in text_lower and len(text) > len(self._longest_seen):
                idx = text_lower.find(seen_lower) + len(seen_lower)
                new_part = text[idx:].strip()
                if len(text) > len(best_extending or ""):
                    best_extending = text
                    best_new_part = new_part

        # Found extending text - return just the new part
        if best_extending:
            self._longest_seen = best_extending
            return best_new_part if best_new_part else (best_extending if not seen_lower else "")

        return ""

    def _poll_captions(self) -> None:
        """Poll the Live Captions window for new text."""
        window = None
        retry_count = 0

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

                # Get current texts from window
                texts = self._get_caption_text(window)

                # Skip if no texts
                if not texts:
                    time.sleep(self._poll_interval)
                    continue

                # Find only the NEW content
                new_content = self._find_new_content(texts)

                if new_content and len(new_content) > 2:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    transcript_entry = f"[{timestamp}] {new_content}"

                    with self._lock:
                        self._transcript_parts.append(transcript_entry)

                    if self.on_transcript:
                        self.on_transcript(transcript_entry)

            except ElementNotFoundError:
                window = None
            except Exception as e:
                print(f"[DEBUG] Error: {e}")
                window = None

            time.sleep(self._poll_interval)

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
        self._longest_seen = ""

        print("=" * 60)
        print("Starting Windows Live Captions capture...")
        print("=" * 60)

        self._open_live_captions()

        self._poll_thread = threading.Thread(target=self._poll_captions, daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        """Stop capturing."""
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
        self._longest_seen = ""

    def save_transcript(self, filepath: str) -> None:
        """Save transcript to a file."""
        with self._lock:
            transcript = "\n".join(self._transcript_parts)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
