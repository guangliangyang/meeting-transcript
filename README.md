# Meeting Assistant

Real-time meeting transcription with AI-powered software development advice.

## Features

- **Real-time Transcription**: Captures meeting audio via Windows Live Captions
- **AI Dev Advice**: Get contextual software development suggestions on-demand
- **Meeting Summary**: Auto-generates comprehensive meeting summaries
- **Action Items**: Extracts action items and decisions from discussions
- **Fallback AI**: Uses Gemini API with Grok (via OpenCLI) as backup

## Requirements

- **Windows 10/11** (uses Windows Live Captions)
- **Python 3.10+**
- **Gemini API key** (optional - will fallback to Grok)
- **OpenCLI** (for Grok fallback, optional)

## Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd meeting-assistant
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install pywinauto
```

4. Configure environment:
```bash
copy .env.example .env
```

5. Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

Get your API key from: https://aistudio.google.com/apikey

## Usage

### Start the Assistant

```bash
python main.py
```

Or use the batch file:
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

The assistant uses Windows Live Captions for transcription. It will auto-open, or you can open manually:

**Press `Win+Ctrl+L`** to open Windows Live Captions

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
├── transcription/       # Transcription module
│   └── realtime.py      # Windows Live Captions integration
├── assistant/           # Dev advisor module
│   └── advisor.py       # AI-powered dev advice
├── summary/             # Summary generation
│   └── generator.py     # Meeting summary & action items
├── ui/                  # User interface
│   └── console.py       # Rich console UI
├── config.py            # Configuration management
├── main.py              # Main entry point
└── requirements.txt     # Python dependencies
```

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

## Dependencies

- `sounddevice` - Audio capture
- `numpy`, `scipy` - Audio processing
- `SpeechRecognition` - Speech recognition
- `google-generativeai` - Gemini API
- `keyboard` - Global hotkeys
- `rich` - Console UI
- `python-dotenv` - Environment config
- `pywinauto` - Windows Live Captions integration

## License

MIT
