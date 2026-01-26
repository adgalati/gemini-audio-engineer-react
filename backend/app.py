import base64
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, Request, BackgroundTasks


from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

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
from audio_pipeline import AudioJobPipeline, start_processing_pipeline
from job_manager import run_heavy_task



app = FastAPI(title="Gemini Audio Engineer API")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # This catches ALL errors (Quota, API keys, Crashes)
    # and forces them to return as JSON so the frontend can read them.
    print(f"🔥 CAUGHT EXCEPTION: {exc}")
    return JSONResponse(
        status_code=400, 
        content={"detail": str(exc)}
    )

# Track which provider each session uses for follow-up routing
_session_providers: dict[str, str] = {}  # session_id -> "gemini" | "openai"

# Create static directory for MIDI files
MIDI_OUTPUT_DIR = "static/midi"
os.makedirs(MIDI_OUTPUT_DIR, exist_ok=True)

# Mount static files for MIDI downloads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dev CORS Next.js default
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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


@app.post("/api/process")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = Form("demucs"),
):
    """
    Starts the full Phase 1 processing pipeline (Stems + MIDI) as a background job.
    Uses Phase 2D job queuing.
    """
    # 1. Save upload to temporary location
    temp_path = _save_upload_to_temp(file)

    # 2. Initialize the job
    pipeline = AudioJobPipeline()
    job_id = pipeline.initialize_job(temp_path)

    # 3. Queue the heavy processing with semaphore enforcement
    background_tasks.add_task(run_heavy_task, start_processing_pipeline, job_id, separation_model=model)

    return {"job_id": job_id, "status_url": f"/api/process/{job_id}"}




@app.get("/api/process/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns the current status of a processing job.
    """
    pipeline = AudioJobPipeline(job_id)
    status = pipeline.get_status()
    if "error" in status:
        return JSONResponse(status_code=404, content=status)
    return status



@app.post("/api/spectrogram")
def spectrogram(
    file: UploadFile = File(...),
    startSec: float = Form(...),
    endSec: float = Form(...),
):
    """
    Returns a Mel spectrogram PNG (base64) for the selected region.
    This does NOT call Gemini — it's just a preview.
    """
    original_path = _save_upload_to_temp(file)
    trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
    spec_png = generate_mel_spectrogram_png(trimmed_path)
    return {"spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8")}


@app.post("/api/analyze")
def analyze(
    file: UploadFile = File(...),
    startSec: float = Form(...),
    endSec: float = Form(...),
    prompt: str = Form(""),
    modelId: str = Form(...),
    temperature: float = Form(0.2),
    thinkingBudget: int = Form(0),
    mode: str = Form("engineer"),
):
    try:
        """
        Trims audio, generates spectrogram, starts Chat Session with Gemini or OpenAI.
        Returns initial advice + session ID.
        """
        original_path = _save_upload_to_temp(file)
        trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
        spec_png = generate_mel_spectrogram_png(trimmed_path)

        # Route to appropriate provider based on model ID
        if modelId.startswith("gpt-"):
            session_id, advice = openai_start_session(
                audio_path=trimmed_path,
                spectrogram_png_bytes=spec_png,
                user_prompt=prompt,
                model_id=modelId,
                temperature=float(temperature),
                mode=mode,
            )
            _session_providers[session_id] = "openai"
        else:
            session_id, advice = gemini_start_session(
                audio_path=trimmed_path,
                spectrogram_png_bytes=spec_png,
                user_prompt=prompt,
                model_id=modelId,
                temperature=float(temperature),
                thinking_budget=thinkingBudget,
                mode=mode,
            )
            _session_providers[session_id] = "gemini"

        # Check for Empty Response
        if advice is None:
            raise Exception("AI Model returned no response. Check API Key and Model ID.")

        # MIDI Generation
        clean_advice, midi_filename = extract_and_generate_midi(advice, MIDI_OUTPUT_DIR)
        midi_url = f"/static/midi/{midi_filename}" if midi_filename else None

        return {
            "sessionId": session_id,
            "advice": clean_advice,
            "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
            "midiDownloadUrl": midi_url,
        }
    except Exception as e:
        # CATCH ALL ERRORS HERE
        print(f"Error in analyze endpoint: {e}")
        # Return a 400 Bad Request with the EXACT error message from Python
        return JSONResponse(
            status_code=400, 
            content={"detail": str(e)} 
        )

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

