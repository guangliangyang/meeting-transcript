"""Transcriber factory for cross-platform support."""

import sys
from typing import Callable, Optional

from transcription.base import BaseTranscriber


def get_transcriber(on_transcript: Optional[Callable[[str], None]] = None) -> BaseTranscriber:
    """Get the appropriate transcriber for the current platform.

    Args:
        on_transcript: Callback called with new transcript text

    Returns:
        Platform-specific transcriber instance

    Raises:
        NotImplementedError: If platform is not supported
        ImportError: If required dependencies are missing
    """
    if sys.platform == 'win32':
        from transcription.windows import WindowsTranscriber
        return WindowsTranscriber(on_transcript)

    elif sys.platform == 'darwin':
        from transcription.macos import MacOSTranscriber
        return MacOSTranscriber(on_transcript)

    else:
        # Linux and others - try macOS implementation (SpeechRecognition is cross-platform)
        try:
            from transcription.macos import MacOSTranscriber
            print(f"[INFO] Using SpeechRecognition transcriber for {sys.platform}")
            return MacOSTranscriber(on_transcript)
        except ImportError:
            raise NotImplementedError(
                f"Platform '{sys.platform}' is not fully supported. "
                "Install SpeechRecognition and PyAudio for basic support."
            )
