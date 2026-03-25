"""Audio capture module using sounddevice."""

import io
import threading
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from typing import Callable, Optional
from config import SAMPLE_RATE, CHANNELS, CHUNK_DURATION_SECONDS


class AudioCapture:
    """Captures audio from microphone and buffers it into chunks."""

    def __init__(self, on_chunk: Optional[Callable[[bytes], None]] = None):
        """
        Initialize audio capture.

        Args:
            on_chunk: Callback function called with audio chunk bytes (WAV format)
        """
        self.sample_rate = SAMPLE_RATE
        self.channels = CHANNELS
        self.chunk_duration = CHUNK_DURATION_SECONDS
        self.on_chunk = on_chunk

        self._buffer: list[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._chunk_thread: Optional[threading.Thread] = None

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info: dict, status: sd.CallbackFlags) -> None:
        """Called by sounddevice for each audio block."""
        if status:
            print(f"Audio status: {status}")

        with self._buffer_lock:
            self._buffer.append(indata.copy())

    def _chunk_worker(self) -> None:
        """Worker thread that processes audio chunks."""
        samples_per_chunk = int(self.sample_rate * self.chunk_duration)

        while self._running:
            # Wait for enough samples
            threading.Event().wait(self.chunk_duration)

            if not self._running:
                break

            with self._buffer_lock:
                if not self._buffer:
                    continue

                # Concatenate all buffered audio
                audio_data = np.concatenate(self._buffer)
                self._buffer.clear()

            if len(audio_data) < samples_per_chunk // 2:
                # Not enough audio, skip
                continue

            # Convert to WAV bytes
            wav_bytes = self._audio_to_wav(audio_data)

            if self.on_chunk:
                try:
                    self.on_chunk(wav_bytes)
                except Exception as e:
                    print(f"Error in chunk callback: {e}")

    def _audio_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        # Ensure audio is in correct format (mono, int16)
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]  # Take first channel

        # Convert float32 to int16
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32767).astype(np.int16)

        # Write to bytes buffer
        buffer = io.BytesIO()
        wavfile.write(buffer, self.sample_rate, audio_data)
        buffer.seek(0)
        return buffer.read()

    def start(self) -> None:
        """Start capturing audio from microphone."""
        if self._running:
            return

        self._running = True
        self._buffer.clear()

        # Start audio stream
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
        )
        self._stream.start()

        # Start chunk processing thread
        self._chunk_thread = threading.Thread(target=self._chunk_worker, daemon=True)
        self._chunk_thread.start()

        print(f"Audio capture started (rate={self.sample_rate}Hz, "
              f"chunk={self.chunk_duration}s)")

    def stop(self) -> bytes:
        """
        Stop capturing audio.

        Returns:
            Final audio chunk as WAV bytes (may be empty)
        """
        self._running = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._chunk_thread:
            self._chunk_thread.join(timeout=2)
            self._chunk_thread = None

        # Return any remaining audio
        with self._buffer_lock:
            if self._buffer:
                audio_data = np.concatenate(self._buffer)
                self._buffer.clear()
                return self._audio_to_wav(audio_data)

        return b""

    def get_current_buffer(self) -> bytes:
        """Get current audio buffer as WAV bytes without clearing."""
        with self._buffer_lock:
            if not self._buffer:
                return b""
            audio_data = np.concatenate(self._buffer)
            return self._audio_to_wav(audio_data)

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        return input_devices
