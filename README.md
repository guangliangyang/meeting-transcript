# Meeting Assistant

Real-time meeting transcription with AI-powered software development advice.

## Features

- **Real-time Transcription**: Cross-platform speech-to-text
  - Windows: Uses Windows Live Captions
  - macOS/Linux: Uses Google Speech Recognition API
- **AI Dev Advice**: Get contextual software development suggestions on-demand
- **Meeting Summary**: Auto-generates comprehensive meeting summaries
- **Action Items**: Extracts action items and decisions from discussions
- **Live Translation**: Shows a Chinese translation under each transcript line
- **Fallback AI**: Uses Gemini API with Grok (via OpenCLI) as backup

## Requirements

- **Python 3.10+**
- **Gemini API key** (optional - will fallback to Grok)
- **OpenCLI** (for Grok fallback, optional)

### Platform-specific
- **Windows**: Windows 10/11 with Live Captions
- **macOS**: macOS 10.15+ with microphone access
- **Linux**: PulseAudio or ALSA for microphone access

## Installation

### All Platforms

1. Clone the repository:
```bash
git clone <repo-url>
cd meeting-assistant
```

2. Create and activate virtual environment:
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. Install base dependencies:
```bash
pip install -r requirements.txt
```

### Windows Setup

```bash
pip install pywinauto
```

### macOS Setup

```bash
# Install portaudio first
brew install portaudio

# Then install PyAudio
pip install pyaudio
```

### Linux Setup

```bash
# Debian/Ubuntu
sudo apt-get install portaudio19-dev python3-pyaudio

# Then install PyAudio
pip install pyaudio
```

### Configure Environment

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

Get your API key from: https://aistudio.google.com/apikey

## Usage

### Start the Assistant

```bash
python main.py
```

Windows users can also use:
```bash
run.bat
```

### Hotkeys

| Key | Action |
|-----|--------|
| `Ctrl+Space` | Get AI dev advice based on current discussion |
| `Ctrl+Q` | End meeting and generate summary |
| `Esc` | Exit application |

### Windows Live Captions

On Windows, the assistant uses Windows Live Captions for transcription. It will auto-open, or you can open manually:

**Press `Win+Ctrl+L`** to open Windows Live Captions

### macOS/Linux

On macOS and Linux, the assistant uses your microphone directly with Google Speech Recognition. Ensure microphone permissions are granted.

## Output

Meeting summaries are saved to the `output/` directory with timestamp:
```
output/meeting_YYYYMMDD_HHMMSS.md
```

Each file contains:
- Meeting summary with key points
- Decisions made
- Action items
- Technical topics discussed
- Full transcript
- AI advice given during the meeting

## Architecture

```
meeting-assistant/
├── ai/                  # AI provider abstraction
│   ├── provider.py      # Base AIProvider interface
│   ├── gemini.py        # Google Gemini implementation
│   ├── grok.py          # Grok via OpenCLI (fallback)
│   └── factory.py       # FallbackProvider (Gemini → Grok)
├── audio/               # Audio capture module
│   └── capture.py       # Microphone capture (sounddevice)
├── transcription/       # Transcription module (cross-platform)
│   ├── base.py          # BaseTranscriber interface
│   ├── windows.py       # Windows Live Captions
│   ├── macos.py         # macOS/Linux Speech Recognition
│   ├── fake.py          # File replay, for testing without audio
│   └── factory.py       # Platform detection & transcriber factory
├── translation/         # Live translation
│   ├── provider.py      # Base TranslationProvider interface
│   ├── _http.py         # Shared session, chunking, cache, rate-limit errors
│   ├── google_cloud.py  # Official Cloud Translation API (needs a key)
│   ├── google_single.py # translate_a/single (unofficial, no key)
│   ├── google_batch.py  # batchexecute (unofficial, no key)
│   ├── factory.py       # Ordered provider chain
│   └── pipeline.py      # Queue + workers + ordered output
├── assistant/           # Dev advisor module
│   └── advisor.py       # AI-powered dev advice
├── summary/             # Summary generation
│   └── generator.py     # Meeting summary & action items
├── ui/                  # User interface
│   ├── console.py       # Rich console UI
│   └── encoding.py      # UTF-8 console setup (required for Chinese)
├── tools/               # Test harnesses (no audio required)
│   ├── check_flush.py   # Transcript flush bookkeeping invariant
│   ├── check_chain.py   # Provider chain fallthrough
│   └── fake_transcript.py  # Replays canned lines through the display path
├── config.py            # Configuration management
├── main.py              # Main entry point
└── requirements.txt     # Python dependencies
```

## Translation

Each transcript line is printed as usual, with its Chinese translation dimmed on
the line below:

```
[10:31:04] The entitlement service needs a new column on the subscription table.
           权利服务需要订阅表上的一个新列。
```

**Providers**, tried in order (`TRANSLATION_PROVIDER=auto`):

| # | Provider | Key needed | Notes |
|---|----------|-----------|-------|
| 1 | **Cloud Translation API** (official) | `GOOGLE_TRANSLATE_API_KEY` | Supported and documented. 500,000 chars/month free, then $20/million. Skipped entirely when no key is set. |
| 2 | `translate_a/single` (unofficial) | none | Zero setup, ~0.5s. Undocumented, rate limited sooner. |
| 3 | `batchexecute` (unofficial) | none | Rate limited less readily, so it makes a good last resort. |

Pin a single stage with `TRANSLATION_PROVIDER=cloud`, `single`, `batch`, or turn it
off with `off`.

**With no key the app still works** — the chain is just 2 → 3, which needs no setup
at all. Adding `GOOGLE_TRANSLATE_API_KEY` silently upgrades it to the supported API.
The startup panel names the stage actually in use.

A word on the unofficial endpoints: they are the backend `translate.google.com`
calls, not published APIs. They have no SLA, can change without notice, and rate
limit with no quota you can inspect. They are a convenience, not a guarantee — set
a key if this matters to you.

**Translation never uses Gemini** and never spends Gemini tokens. Gemini still
powers the meeting summary and Ctrl+Space advice.

**Translation is display-only.** The saved `.md`, the AI advice and the meeting
summary always use the original English.

**It never blocks the meeting.** A line waits at most
`TRANSLATION_MAX_HOLD_SECONDS` (default 3s) for its translation, then prints
without one. If translation fails repeatedly the app stops attempting it for a
cooldown period, so being offline costs no ongoing delay.

Turn it off with `TRANSLATION_ENABLED=false`.

### Chinese not rendering?

If you see boxes or question marks instead of Chinese, the encoding or the font
is the problem, not the translation:

- Use **Windows Terminal**, or set the console font to Consolas / Cascadia Mono.
  The legacy console with a raster font cannot draw CJK.
- `run.bat` sets UTF-8 for you; `main.py` also sets it in code, which is what
  covers the packaged `.exe`.

### Why not a Windows translation API?

There isn't one. Per the official
[Windows AI APIs list](https://learn.microsoft.com/en-us/windows/ai/apis/),
Live Translation is listed under **Planned features — not yet supported**. The
shipping Windows AI APIs cover Phi Silica, OCR, speech recognition and imaging;
none of them translate text, and they are C#/C++ only with no Python projection
for the `Microsoft.Windows.*` types.

The Live Captions *feature* can translate, but only on a Copilot+ PC (40+ TOPS
NPU). Phi Silica could translate by prompting, but it needs C# and is being
replaced by Aion Instruct in late 2026.

## AI Providers

The assistant uses a fallback pattern for AI:

1. **Primary: Gemini** - Google's Gemini 2.5 Flash model
2. **Fallback: Grok** - Via OpenCLI browser automation

If Gemini fails (API error, rate limit, etc.), it automatically falls back to Grok.

### Grok Setup (Optional)

For Grok fallback support:

1. Install OpenCLI: https://github.com/jackwener/opencli
2. Login to grok.com in your browser
3. The assistant will use Grok when Gemini is unavailable

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | (required for Gemini) |
| `GROK_TIMEOUT` | Grok response timeout (seconds) | 120 |
| `TRANSLATION_ENABLED` | Show live translation | `true` |
| `GOOGLE_TRANSLATE_API_KEY` | Official Cloud Translation key (optional) | (unset) |
| `TRANSLATION_PROVIDER` | `auto`, `cloud`, `single`, `batch` or `off` | `auto` |
| `TRANSLATION_TARGET_LANG` | Target language code | `zh-CN` |
| `TRANSLATION_TIMEOUT` | Per-request timeout (seconds) | 3.0 |
| `TRANSLATION_MAX_HOLD_SECONDS` | Max delay a line waits for its translation | 3.0 |
| `TRANSLATION_WORKERS` | Translation worker threads | 1 |
| `TRANSCRIPT_MIN_FLUSH_SECONDS` | Earliest a transcript line is emitted | 1.5 |
| `TRANSCRIPT_MAX_FLUSH_SECONDS` | Latest a transcript line is emitted | 6.0 |
| `ADVICE_CONTEXT_ENTRIES` | Transcript entries sent to the advisor | 40 |

## Dependencies

### Core
- `SpeechRecognition` - Speech recognition
- `google-generativeai` - Gemini API
- `keyboard` - Global hotkeys
- `rich` - Console UI
- `python-dotenv` - Environment config
- `requests` - Translation HTTP client

### Audio
- `sounddevice` - Audio capture
- `numpy`, `scipy` - Audio processing

### Platform-specific
- `pywinauto` - Windows Live Captions integration (Windows only)
- `pyaudio` - Microphone access (macOS/Linux)

## License

MIT
