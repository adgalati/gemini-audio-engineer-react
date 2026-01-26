# gemini-audio-engineer-react

A vibe-coded **Mix Assistant AI** that provides "expert" audio engineering feedback:

- **Next.js (App Router) frontend**: Upload audio, waveform playback with region selection (WaveSurfer), chat-based consultation
- **FastAPI backend**: Trims selected audio regions, generates Mel spectrograms, and provides AI-powered mixing advice
- **Multi-model support**: Choose between Gemini (with spectrogram analysis) or OpenAI GPT Audio models

## Features

- 🎵 **Audio Analysis**: Upload WAV, MP3, or FLAC files and select specific regions for analysis
- 📊 **Spectrogram Generation**: Visual frequency analysis to identify issues
- 🤖 **AI Consultation**: Get professional mixing and mastering advice from AI models
- 💬 **Chat Interface**: Follow-up conversations to drill deeper into specific issues
- 🎛️ **Multiple Models**: Support for Gemini 3, Gemini 2, and OpenAI GPT Audio models

---

## 1) Backend Setup

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### Environment Configuration

Copy the example environment file and configure your API keys:

```bash
# Windows:
copy .env.example .env

# macOS/Linux:
cp .env.example .env
```

Then edit `.env` with your API keys:

```env
# Required for Gemini models (gemini-3-pro, gemini-3-flash, gemini-2.0, etc.)
GEMINI_API_KEY=your_gemini_api_key_here

# Required for OpenAI GPT Audio model
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Only needed if FFmpeg is not in your system PATH
FFMPEG_PATH=
```

> **Note:** You only need to configure the API key(s) for the model(s) you plan to use.

### FFmpeg Dependency

FFmpeg is required for audio processing. Install it based on your OS:

**Windows (WinGet):**
```powershell
winget install Gyan.FFmpeg
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Linux (apt):**
```bash
sudo apt install ffmpeg
```

> If FFmpeg is installed but the app can't find it, set the `FFMPEG_PATH` variable in your `.env` file to point to the directory containing `ffmpeg.exe` (Windows) or `ffmpeg` binary.

### Run the API

```bash
uvicorn app:app --reload --port 8000
```

Health check: Open `http://localhost:8000/health`

---

## 2) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## Usage

1. **Upload Audio**: Select a WAV, MP3, or FLAC file
2. **Select Region**: Click and drag on the waveform to select the section you want analyzed
3. **Choose Model**: Select from available Gemini or OpenAI models
4. **Enter Prompt**: Describe what you want feedback on (e.g., "Check the overall frequency balance")
5. **Start Analysis**: Click the button to get AI-powered mixing advice
6. **Follow Up**: Use the chat to ask follow-up questions about specific issues

## Model Differences

| Model | Spectrogram | Thinking Mode | Best For |
|-------|-------------|---------------|----------|
| Gemini 3 Pro | ✅ | ✅ | Deep analysis with visual + audio |
| Gemini 3 Flash | ✅ | ✅ | Fast analysis with visual + audio |
| Gemini 2.0 Thinking | ✅ | ✅ | Complex problem-solving |
| Gemini 2.0 Flash | ✅ | ❌ | Quick responses |
| GPT Audio | ❌ | ❌ | Audio-only analysis |

---

## Notes

- **"Preview"** generates only the spectrogram (no AI call) so you can see the visual first
- **"Start Analysis"** trims audio + generates spectrogram + sends to AI for comprehensive feedback
- Gemini models receive both the audio file and spectrogram image for analysis
- GPT Audio model receives only the audio (does not support image input)
