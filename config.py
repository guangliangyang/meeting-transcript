"""Configuration management for Meeting Assistant."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import yaml

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

# Grok settings (via OpenCLI)
GROK_TIMEOUT = int(os.getenv("GROK_TIMEOUT", "120"))

def validate_config():
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY:
        print(
            "[WARN] GEMINI_API_KEY not found. "
            "Will use Grok fallback if available. "
            "Get Gemini key from: https://aistudio.google.com/apikey"
        )


# Prompt configuration
def _get_prompts_path() -> Path:
    """Get the path to prompts.yaml, handling PyInstaller bundling."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_path = Path(sys.executable).parent
    else:
        # Running as script
        base_path = PROJECT_ROOT
    return base_path / "prompts.yaml"


def load_prompts() -> dict:
    """Load prompts from prompts.yaml file."""
    prompts_path = _get_prompts_path()

    if not prompts_path.exists():
        raise FileNotFoundError(
            f"prompts.yaml not found at {prompts_path}. "
            "Please ensure prompts.yaml is in the same directory as the executable."
        )

    with open(prompts_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# Load prompts at module import
_prompts = None

def get_prompts() -> dict:
    """Get loaded prompts, loading from file if needed."""
    global _prompts
    if _prompts is None:
        _prompts = load_prompts()
    return _prompts


# Convenience functions for accessing specific prompts
def get_summary_prompt(name: str) -> str:
    """Get a summary prompt by name."""
    return get_prompts()['summary'][name]


def get_advisor_prompt(name: str) -> str:
    """Get an advisor prompt by name."""
    return get_prompts()['advisor'][name]
