import base64
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from audio_processor import trim_audio_to_temp, generate_mel_spectrogram_png
from gemini_client import (
    start_audio_chat_session as gemini_start_session,
    send_chat_message as gemini_send_message,
)
from openai_client import (
    start_audio_chat_session as openai_start_session,
    send_chat_message as openai_send_message,
)

app = FastAPI(title="Gemini Audio Engineer API")

# Track which provider each session uses for follow-up routing
_session_providers: dict[str, str] = {}  # session_id -> "gemini" | "openai"

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
    prompt: str = Form(...),
    modelId: str = Form(...),
    temperature: float = Form(0.2),
    thinkingBudget: int = Form(0),
):
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
        )
        _session_providers[session_id] = "openai"
    else:
        session_id, advice = gemini_start_session(
            audio_path=trimmed_path,
            spectrogram_png_bytes=spec_png,
            user_prompt=prompt,
            model_id=modelId,
            temperature=float(temperature),
            thinking_budget=thinkingBudget
        )
        _session_providers[session_id] = "gemini"

    return {
        "sessionId": session_id,
        "advice": advice,
        "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
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
    return {"reply": reply}
