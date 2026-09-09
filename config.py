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
# Official Cloud Translation API. When set, translation uses the supported API
# instead of the unofficial endpoints. Not related to GEMINI_API_KEY.
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")

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


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable."""
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# Translation settings (shown under each transcript line; display only)
TRANSLATION_ENABLED = _env_bool("TRANSLATION_ENABLED", True)
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "auto")  # auto|cloud|single|batch|off
TRANSLATION_SOURCE_LANG = os.getenv("TRANSLATION_SOURCE_LANG", "en")
TRANSLATION_TARGET_LANG = os.getenv("TRANSLATION_TARGET_LANG", "zh-CN")
TRANSLATION_TIMEOUT = float(os.getenv("TRANSLATION_TIMEOUT", "3.0"))
TRANSLATION_CONNECT_TIMEOUT = float(os.getenv("TRANSLATION_CONNECT_TIMEOUT", "2.0"))
TRANSLATION_RETRIES = int(os.getenv("TRANSLATION_RETRIES", "1"))
# Safety net for pathological input only. Measured: the endpoint returns ~9.7k
# chars intact in one request, and splitting is strictly slower (chunks go
# sequentially), so this is set well above any realistic transcript segment.
TRANSLATION_MAX_CHUNK_CHARS = int(os.getenv("TRANSLATION_MAX_CHUNK_CHARS", "4000"))
# requests.Session is not documented thread-safe; >1 worker needs one per worker.
TRANSLATION_WORKERS = int(os.getenv("TRANSLATION_WORKERS", "1"))
TRANSLATION_QUEUE_MAX = int(os.getenv("TRANSLATION_QUEUE_MAX", "32"))
TRANSLATION_MAX_HOLD_SECONDS = float(os.getenv("TRANSLATION_MAX_HOLD_SECONDS", "3.0"))
TRANSLATION_MIN_CHARS = int(os.getenv("TRANSLATION_MIN_CHARS", "3"))
TRANSLATION_FAILURE_THRESHOLD = int(os.getenv("TRANSLATION_FAILURE_THRESHOLD", "3"))
TRANSLATION_COOLDOWN_SECONDS = float(os.getenv("TRANSLATION_COOLDOWN_SECONDS", "60"))

# Transcript flush cadence (Windows Live Captions).
# NOTE: raising TRANSCRIPT_MAX_FLUSH_SECONDS produces longer segments and so
# slower translations - raise TRANSLATION_MAX_HOLD_SECONDS with it, or long
# segments will systematically print untranslated.
TRANSCRIPT_MIN_FLUSH_SECONDS = float(os.getenv("TRANSCRIPT_MIN_FLUSH_SECONDS", "1.5"))
TRANSCRIPT_MAX_FLUSH_SECONDS = float(os.getenv("TRANSCRIPT_MAX_FLUSH_SECONDS", "6.0"))
TRANSCRIPT_MIN_FLUSH_CHARS = int(os.getenv("TRANSCRIPT_MIN_FLUSH_CHARS", "25"))
# Live Captions can be configured with punctuation off, in which case no
# sentence terminator ever appears - this is the fallback cut point.
TRANSCRIPT_MAX_PENDING_WORDS = int(os.getenv("TRANSCRIPT_MAX_PENDING_WORDS", "40"))

# Advice context - sized against the flush cadence above, not a raw entry count.
ADVICE_CONTEXT_ENTRIES = int(os.getenv("ADVICE_CONTEXT_ENTRIES", "40"))
ADVICE_CONTEXT_MAX_CHARS = int(os.getenv("ADVICE_CONTEXT_MAX_CHARS", "8000"))

def validate_config():
    """Validate that required configuration is present."""
    if not GEMINI_API_KEY:
        print(
            "[WARN] GEMINI_API_KEY not found. "
            "Will use Grok fallback if available. "
            "Get Gemini key from: https://aistudio.google.com/apikey"
        )
    if TRANSLATION_PROVIDER.strip().lower() == "cloud" and not GOOGLE_TRANSLATE_API_KEY:
        print(
            "[WARN] TRANSLATION_PROVIDER=cloud but GOOGLE_TRANSLATE_API_KEY is not set. "
            "Translation is disabled. Use TRANSLATION_PROVIDER=auto to fall back "
            "to the unofficial endpoints."
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

