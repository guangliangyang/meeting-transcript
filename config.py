"""Configuration management for Meeting Assistant."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Audio settings
SAMPLE_RATE = 16000  # 16kHz for speech recognition
CHANNELS = 1  # Mono audio
CHUNK_DURATION_SECONDS = 5  # Send audio to Gemini every N seconds

# Paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Hotkeys
HOTKEY_GET_ADVICE = "ctrl+space"
HOTKEY_END_MEETING = "ctrl+q"
HOTKEY_EXIT = "esc"

# Gemini settings
GEMINI_MODEL = "gemini-2.5-flash"

def validate_config():
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not found. "
            "Please create a .env file with your API key. "
            "Get one from: https://aistudio.google.com/apikey"
        )
