# Gemini Audio Engineer: Professional Studio Maturation

A vibe-coded **Mix Assistant AI** that has evolved into a professional-grade studio assistant, bridging the gap between raw audio and a ready-to-mix DAW session.

- **Next.js (App Router) frontend**: Real-time waveform analysis, multi-track studio mixer, and MIDI piano roll preview.
- **FastAPI backend**: Heavy-duty audio processing pipeline with background job queuing and GPU acceleration.
- **Professional Pipeline**: Multi-model stem separation (Demucs/UMX), polyphonic MIDI extraction (basic-pitch), and Gemini musical validation.

## 🚀 Key Features

### 1. 🎛️ AI Consultation & Analysis
- **Spectrogram Preview**: Visual frequency analysis to identify mix issues.
- **Multi-Model Support**: Gemini 2.0/3.0 (Visual + Audio) and OpenAI GPT Audio.
- **Contextual Chat**: Professional mixing advice with a persistent consultation session.

### 2. 🎼 Deep Stem Separation
Splits a full track into **9 distinct stems** using ML-based separation (Demucs v4 / Open-Unmix):
- **Vocals**: Lead & Backing (stereo-field isolated).
- **Drums**: Kick, Snare, and Hats (spectral-filtered).
- **Instruments**: Bass, Guitars, Keys/Synth, and Harmony.

### 3. 🎹 Structured MIDI Extraction
Automated polyphonic transcription using **Spotify's basic-pitch**:
- Generates mapped MIDI files for Melody, Bass, Guitars, and Keys.
- **Gemini Musical Validation**: AI audits every MIDI file for pitch, rhythm, and harmonic correctness.

### 4. 🏁 DAW Integration (REAPER)
- **One-Click Export**: Generates a standard `.RPP` (REAPER Project) file.
- **Automated Routing**: Stems and MIDI are pre-mapped to color-coded tracks, ready for mixing.

---

## 🛠️ 1) Backend Setup

```bash
cd backend
python -m venv .venv

# Activate:
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

### Dependencies Note
For professional stem and MIDI features, ensure the following are installed:
`demucs`, `openunmix`, `basic-pitch`, `pretty-midi`, `librosa`, `soundfile`, `torch`.

### Environment Configuration
Copy `.env.example` to `.env` and add:
- `GEMINI_API_KEY`: Required for analysis and MIDI validation.
- `FFMPEG_PATH`: (Optional) Path to FFmpeg binaries if not in PATH.

### FFmpeg Dependency
FFmpeg is required for audio extraction.
- **Windows**: `winget install Gyan.FFmpeg`
- **macOS**: `brew install ffmpeg`

### ⚡ Run the API
```bash
uvicorn app:app --reload --port 8000
```

---

## 🎨 2) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000`

---

## 🎹 Professional Workflow

1. **Upload & Analyze**: Use the "Engineer" or "Producer" modes for immediate AI feedback.
2. **Deep Extraction**: Toggle between **Demucs v4** or **Open-Unmix** and start a background job.
3. **Mix & Audit**: Audition your stems in the **In-Browser Mixer** and check the **MIDI Piano Roll**.
4. **Validation**: Read the **Gemini Validation Report** for musical critique.
5. **DAW Sync**: Download the `.RPP` project and start producing!

---

## 🏗️ Architecture
- **Job Manager**: Uses an async semaphore to prevent GPU VRAM exhaustion during heavy ML tasks.
- **Pipeline Orchestration**: Chained processing from raw upload -> 4-stem split -> 9-track refinement -> MIDI extraction -> AI Validation -> RPP Generation.
- **Static Store**: Filesystem-based persistence for long-running jobs.

---

### Model Comparison

| Model | Multi-Track | MIDI Logic | Best For |
|-------|-------------|------------|----------|
| Gemini 3 Pro | ✅ Visuals | ✅ Pro | Advanced Production Advice |
| Gemini 2.0 Flash | ✅ Speed | ✅ Fast | General Mix Checks |
| GPT Audio | ❌ Visuals | ❌ No | Pure Audio Conversations |
| Local ML (Demucs) | ✅ Stems | ✅ MIDI | Source Extraction |
