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
    import traceback
    error_msg = f"🔥 CAUGHT EXCEPTION: {str(exc)}\n{traceback.format_exc()}"
    print(error_msg)
    return JSONResponse(
        status_code=400, 
        content={"detail": str(exc), "traceback": traceback.format_exc()}
    )


# Track which provider each session uses for follow-up routing
_session_providers: dict[str, str] = {}  # session_id -> "gemini" | "openai"

# Mount audio_jobs directory for artifact access (includes all jobs and their internal folders)
app.mount("/audio_jobs", StaticFiles(directory="audio_jobs"), name="audio_jobs")


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
    job_id: Optional[str] = Form(None),
):
    if job_id in ["undefined", "null", "None", ""]:
        job_id = None
    
    print(f"📥 Received /api/process request for job_id: {job_id}")
    temp_path = _save_upload_to_temp(file)

    # 2. Initialize or retrieve the job
    pipeline = AudioJobPipeline(job_id)
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
    # Fix: Correctly check if there is an ACTUAL error message
    if status.get("error") is not None:
        return JSONResponse(status_code=400, content=status)
    
    if "error" in status and status["error"] == "Job not found":
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
    job_id: Optional[str] = Form(None),
):
    if job_id in ["undefined", "null", "None", ""]:
        job_id = None
    
    print(f"📥 Received /api/analyze request for job_id: {job_id}")
    try:
        """
        Trims audio, generates spectrogram, starts Chat Session with Gemini or OpenAI.
        Everything is consolidated under audio_jobs/<job_id>/.
        Returns initial advice + job_id as session ID.
        """
        original_path = _save_upload_to_temp(file)
        trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
        spec_png = generate_mel_spectrogram_png(trimmed_path)

        # Initialize/Retrieve Job
        pipeline = AudioJobPipeline(job_id)
        job_id = pipeline.initialize_job(original_path) # Ensure input.wav exists in job folder

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

        # Save AI Advice to Analysis Folder
        print(f"📝 Saving analysis advice for job {job_id}...")
        pipeline.save_analysis(advice)

        print(f"✅ Analysis for job {job_id} complete. Returning response.")
        return {
            "sessionId": session_id,
            "job_id": job_id,
            "advice": advice,
            "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
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
    jobId: Optional[str] = Form(None),
):
    """
    Send a follow-up message to an active session.
    """
    provider = _session_providers.get(sessionId, "gemini")
    if provider == "openai":
        reply = openai_send_message(sessionId, message)
    else:
        reply = gemini_send_message(sessionId, message)

    if not reply:
        raise Exception("AI Model returned no response.")

    # If we have a jobId, save this follow-up advice
    if jobId:
        pipeline = AudioJobPipeline(jobId)
        # Append to advice instead of overwriting, or save as a separate follow-up
        advice_path = os.path.join(pipeline.analysis_dir, "advice.txt")
        with open(advice_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- Follow-up ---\nUser: {message}\nAI: {reply}")

    return {
        "reply": reply,
    }

@app.get("/api/jobs/{job_id}/analysis")
def download_advice(job_id: str):
    """
    Returns the advice.txt file for a specific job.
    """
    pipeline = AudioJobPipeline(job_id)
    advice_path = os.path.join(pipeline.analysis_dir, "advice.txt")
    if not os.path.exists(advice_path):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Advice not found"})
    
    from fastapi.responses import FileResponse
    return FileResponse(
        advice_path, 
        media_type="text/plain", 
        filename=f"mixing_advice_{job_id[:8]}.txt"
    )

@app.get("/api/jobs/{job_id}/midi-list")
def list_midi_files(job_id: str):
    """
    Dynamically lists all MIDI files available for a specific job.
    This allows the UI to show tracks that were generated but not hardcoded.
    """
    pipeline = AudioJobPipeline(job_id)
    if not os.path.exists(pipeline.midi_dir):
        return {"midi": []}
    
    files = [f for f in os.listdir(pipeline.midi_dir) if f.endswith(".mid")]
    return {"midi": files}

