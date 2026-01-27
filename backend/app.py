import base64
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from audio_processor import trim_audio_to_temp, generate_mel_spectrogram_png
from gemini_client import (
    start_audio_chat_session as gemini_start_session,
    send_chat_message as gemini_send_message,
)
from openai_client import (
    start_audio_chat_session as openai_start_session,
    send_chat_message as openai_send_message,
)
from midi_engine import extract_and_generate_midi
from tempo_analyzer import detect_tempo
from chordino import extract_chords, chords_to_beats, format_chords_for_llm

app = FastAPI(title="Gemini Audio Engineer API")

# Track which provider each session uses for follow-up routing
_session_providers: dict[str, str] = {}  # session_id -> "gemini" | "openai"

# Create static directory for MIDI files
MIDI_OUTPUT_DIR = "static/midi"
os.makedirs(MIDI_OUTPUT_DIR, exist_ok=True)

# Mount static files for MIDI downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dev CORS (Vite default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1].lower() or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.file.read())
        return tmp.name


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/spectrogram")
def spectrogram(
    file: UploadFile = File(...),
    startSec: float = Form(...),
    endSec: float = Form(...),
):
    """
    Returns a Mel spectrogram PNG (base64), detected BPM, and chord progression.
    This does NOT call Gemini — it's just a preview.
    """
    original_path = _save_upload_to_temp(file)
    trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
    spec_png = generate_mel_spectrogram_png(trimmed_path)
    
    # Detect tempo
    bpm, beat_times = detect_tempo(trimmed_path)
    
    # Extract chords and convert to beat-based format
    raw_chords = extract_chords(trimmed_path)
    chords = chords_to_beats(raw_chords, bpm)
    
    return {
        "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
        "bpm": round(bpm, 1),
        "chords": chords
    }


@app.post("/api/analyze")
def analyze(
    file: UploadFile = File(...),
    startSec: float = Form(...),
    endSec: float = Form(...),
    prompt: str = Form(...),
    modelId: str = Form(...),
    temperature: float = Form(0.2),
    thinkingBudget: int = Form(0),
    mode: str = Form("engineer"),
    bpm: Optional[float] = Form(None),  # User-edited BPM from frontend
    chords: Optional[str] = Form(None),  # User-edited chords JSON from frontend
):
    """
    Trims audio, generates spectrogram, starts Chat Session with Gemini or OpenAI.
    Returns initial advice + session ID.
    """
    original_path = _save_upload_to_temp(file)
    trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
    spec_png = generate_mel_spectrogram_png(trimmed_path)
    
    # For Producer mode, use user-provided BPM/chords OR detect if not provided
    import json
    musical_context = ""
    final_bpm = bpm
    final_chords = []
    
    if mode == "producer":
        # Parse chords JSON if provided
        if chords:
            try:
                final_chords = json.loads(chords)
            except json.JSONDecodeError:
                final_chords = []
        
        # If no user-provided data, detect it
        if not final_bpm or not final_chords:
            detected_bpm, beat_times = detect_tempo(trimmed_path)
            raw_chords = extract_chords(trimmed_path)
            
            if not final_bpm:
                final_bpm = detected_bpm
            if not final_chords:
                final_chords = chords_to_beats(raw_chords, detected_bpm)
        
        # Format for LLM
        if final_chords and final_bpm:
            musical_context = format_chords_for_llm(final_chords, final_bpm)
    
    # Prepend musical context to user prompt if available
    enhanced_prompt = f"{musical_context}\n\n{prompt}" if musical_context else prompt

    # Route to appropriate provider based on model ID
    if modelId.startswith("gpt-"):
        session_id, advice = openai_start_session(
            audio_path=trimmed_path,
            spectrogram_png_bytes=spec_png,
            user_prompt=enhanced_prompt,
            model_id=modelId,
            temperature=float(temperature),
            mode=mode,
        )
        _session_providers[session_id] = "openai"
    else:
        session_id, advice = gemini_start_session(
            audio_path=trimmed_path,
            spectrogram_png_bytes=spec_png,
            user_prompt=enhanced_prompt,
            model_id=modelId,
            temperature=float(temperature),
            thinking_budget=thinkingBudget,
            mode=mode,
        )
        _session_providers[session_id] = "gemini"

    # Process MIDI data from response (Producer mode)
    clean_advice, midi_filename = extract_and_generate_midi(advice, MIDI_OUTPUT_DIR)
    midi_url = f"/static/midi/{midi_filename}" if midi_filename else None

    return {
        "sessionId": session_id,
        "advice": clean_advice,
        "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
        "midiDownloadUrl": midi_url,
        "bpm": final_bpm,
        "chords": final_chords,
    }


@app.post("/api/chat")
def chat_reply(
    sessionId: str = Form(...),
    message: str = Form(...),
):
    """
    Send a follow-up message to an active session.
    """
    provider = _session_providers.get(sessionId, "gemini")
    if provider == "openai":
        reply = openai_send_message(sessionId, message)
    else:
        reply = gemini_send_message(sessionId, message)

    # Process MIDI data from response
    clean_reply, midi_filename = extract_and_generate_midi(reply, MIDI_OUTPUT_DIR)
    midi_url = f"/static/midi/{midi_filename}" if midi_filename else None

    return {
        "reply": clean_reply,
        "midiDownloadUrl": midi_url,
    }

