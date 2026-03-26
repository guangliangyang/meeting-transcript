"""Transcription module with cross-platform support."""

from .base import BaseTranscriber
from .factory import get_transcriber

# Backward compatibility alias
try:
    from .windows import WindowsTranscriber as RealtimeTranscriber
except ImportError:
    from .macos import MacOSTranscriber as RealtimeTranscriber

__all__ = ['BaseTranscriber', 'get_transcriber', 'RealtimeTranscriber']
