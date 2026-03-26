"""Real-time transcription for macOS using SpeechRecognition."""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

import speech_recognition as sr

from transcription.base import BaseTranscriber


class MacOSTranscriber(BaseTranscriber):
    """Captures transcription using microphone and Google Speech Recognition.

    Works on macOS (and other platforms) using SpeechRecognition library.
    Uses Google's free speech recognition API.
    """

    def __init__(self, on_transcript: Optional[Callable[[str], None]] = None):
        super().__init__(on_transcript)

        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()

        self._transcript_parts: list[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._listen_thread: Optional[threading.Thread] = None

        # Adjust for ambient noise on first use
        self._calibrated = False

        # Settings
        self._phrase_timeout = 3  # Seconds of silence to end a phrase
        self._energy_threshold = 300  # Minimum audio energy to consider

    def _calibrate_microphone(self) -> None:
        """Calibrate microphone for ambient noise."""
        if self._calibrated:
            return

        print("[INFO] Calibrating microphone for ambient noise...")
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=2)
            self._calibrated = True
            print("[INFO] Microphone calibrated!")
        except Exception as e:
            print(f"[WARN] Calibration failed: {e}")

    def _listen_loop(self) -> None:
        """Continuously listen and transcribe."""
        print("[INFO] Listening for speech...")

        while self._running:
            try:
                with self._microphone as source:
                    # Listen for audio with timeout
                    try:
                        audio = self._recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=30
                        )
                    except sr.WaitTimeoutError:
                        # No speech detected, continue listening
                        continue

                # Transcribe in background to not block listening
                threading.Thread(
                    target=self._transcribe_audio,
                    args=(audio,),
                    daemon=True
                ).start()

            except Exception as e:
                if self._running:
                    print(f"[DEBUG] Listen error: {e}")
                time.sleep(0.5)

    def _transcribe_audio(self, audio: sr.AudioData) -> None:
        """Transcribe audio data using Google Speech Recognition."""
        try:
            # Use Google's free speech recognition
            text = self._recognizer.recognize_google(audio)

            if text and text.strip():
                timestamp = datetime.now().strftime("%H:%M:%S")
                transcript_entry = f"[{timestamp}] {text}"

                with self._lock:
                    self._transcript_parts.append(transcript_entry)

                if self.on_transcript:
                    self.on_transcript(transcript_entry)

        except sr.UnknownValueError:
            # Speech was unintelligible
            pass
        except sr.RequestError as e:
            print(f"[WARN] Speech recognition service error: {e}")
        except Exception as e:
            print(f"[DEBUG] Transcription error: {e}")

    def start(self) -> None:
        """Start capturing and transcribing."""
        if self._running:
            return

        self._running = True

        print("=" * 60)
        print("Starting macOS Speech Recognition...")
        print("Using Google Speech Recognition API")
        print("=" * 60)

        # Calibrate microphone
        self._calibrate_microphone()

        # Start listening thread
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop(self) -> None:
        """Stop capturing."""
        self._running = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2)

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

    def save_transcript(self, filepath: str) -> None:
        """Save transcript to a file."""
        with self._lock:
            transcript = "\n".join(self._transcript_parts)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Transcript\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(transcript)
