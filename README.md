# gemini-audio-engineer-react

A minimal “Mix Assistant” foundation:
- **React (Vite) frontend**: upload audio, waveform playback, region selection (WaveSurfer Regions), prompt box
- **FastAPI backend**: trims the selected region, generates a Mel spectrogram, and (optionally) calls Gemini via `google-genai`

## 1) Backend setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # (Windows) or: cp .env.example .env
# then edit .env and set GEMINI_API_KEY
```

Run the API:

```bash
uvicorn app:app --reload --port 8000
```

Health check: open `http://localhost:8000/health`

## 2) Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## Notes

- “Generate Spectrogram” calls **your backend only** (no Gemini) so you can preview the visual first.
- “Analyze” trims + spectrogram + Gemini analysis and returns the advice + the spectrogram.
- Model IDs are selectable; availability depends on your account/region.
