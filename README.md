# Gemini Audio Engineer (Backend & Web Interface) 🧠🎛️

This repository contains the intelligence layer for the **Gemini Audio Engineer** ecosystem. It provides a FastAPI server that acts as the bridge between your Digital Audio Workstation (via the AUv3 plugin) and Google's Gemini AI.

## 🌟 Overview

When the AUv3 plugin captures audio from your DAW, it sends it here. This backend handles:
1. **Audio Processing:** Slicing, normalizing, and generating detailed spectrograms of the captured audio.
2. **AI Inference:** Packaging the audio context and spectrograms and sending them to Gemini with specialized Mixing, Producing, and Executing prompts.
3. **Chord & Tempo Detection:** Automatically analyzes incoming audio (via Chordino) to give the AI full musical context.
4. **MIDI Generation:** Parsing rhythmic and melodic concepts proposed by the AI to generate downloadable `.mid` files.
5. **DSP Parsing:** Converting the AI's natural language mixing advice into a strict, structured JSON payload.
6. **Delivery:** Serving that JSON and MIDI back to the AUv3 plugin so it can instantly apply the EQ, Compression, Saturation, De-essing, and Reverb parameters to your track.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- A valid Google Gemini API key

### Installation
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Set up your virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Set your environment variables in `.env`:
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```

### Running the Server
Run the FastAPI application using `uvicorn`:
```bash
source .venv/bin/activate
uvicorn app:app --reload --port 8000
```
The AUv3 plugin automatically polls `http://localhost:8000/health` to confirm the connection.

## 🧩 Operating Modes & Prompts

The backend provides three specialized system prompt personas located in `backend/prompts.py`:

- **🎧 Engineer Mode (`ENGINEER_PROMPT`):** Acts as a mixing and mastering consultant. Analyzes the audio and spectrogram to deliver technical critiques and advice on spectral masking, dynamic headroom, and tonal balance. It produces pure text guidance without DSP actions.
- **🎹 Producer Mode (`PRODUCER_PROMPT`):** Acts as an arranger and songwriter. Receives detected BPM and harmonic chord progressions, suggesting complementary instruments, layers, and counter-melodies. Employs the **MIDI Output Protocol** to return structured musical data in `<MIDI_DATA>` tags for automatic `.mid` file compilation.
- **⚡ Executor Mode (`EXECUTOR_PROMPT`):** The automated DSP execution engine. Diagnoses mix problems, provides technical reasoning, and generates strict, structured `<DSP_ACTIONS>` tags (EQ, Compression, De-esser, Saturation, Reverb, Stereo width). **This is the only mode that enables the "Apply AI Mix" / "Apply These Mix Changes" buttons** in the AUv3 plugin and web interface.

If you want to train the AI to focus on specific genres or add new DSP tools, check out `backend/prompts.py` and `backend/dsp_parser.py`. The AI has been heavily tuned to provide conservative, realistic mixing moves rather than destructive changes.

## 🔌 DAW Integration (AUv3 Plugin)
This backend is designed to work in tandem with the **Gemini Audio Engineer AUv3 Plugin** (for Logic Pro and other Apple DAWs). 
You can find the plugin repository and installation instructions here:
👉 **[gemini-au-plugin Repository](https://github.com/dschmidtadv/gemini-au-plugin)**

## 🙏 Acknowledgements & Attribution

This project is a collaborative fork extending the work of:
- **[Anthony Galati (@adgalati)](https://github.com/adgalati):** Original creator of [gemini-audio-engineer-react](https://github.com/adgalati/gemini-audio-engineer-react), who created the core architecture bridging DAWs and Google's Gemini AI.
- **[Maui-B](https://github.com/Maui-B):** Major contributor who enhanced the audio processing pipeline with Demucs stem separation and multi-phase workflows.
