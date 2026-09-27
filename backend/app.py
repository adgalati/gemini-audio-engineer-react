import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))
import base64
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
from dsp_parser import extract_dsp_actions
from audio_pipeline import AudioJobPipeline, start_processing_pipeline, BASE_JOBS_DIR
from job_manager import run_heavy_task
from tempo_analyzer import detect_tempo
from chordino import extract_chords, chords_to_beats, format_chords_for_llm


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

# Ensure audio_jobs directory exists and mount for artifact access
os.makedirs(BASE_JOBS_DIR, exist_ok=True)
app.mount("/audio_jobs", StaticFiles(directory=BASE_JOBS_DIR), name="audio_jobs")


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
    prompt: str = Form(""),
    modelId: str = Form(...),
    temperature: float = Form(0.2),
    thinkingBudget: int = Form(0),
    mode: str = Form("engineer"),
    job_id: Optional[str] = Form(None),
    bpm: Optional[float] = Form(None),
    chords: Optional[str] = Form(None),
):
    if job_id in ["undefined", "null", "None", ""]:
        job_id = None
    
    print(f"📥 Received /api/analyze request for job_id: {job_id}")
    try:
        original_path = _save_upload_to_temp(file)
        trimmed_path = trim_audio_to_temp(original_path, startSec, endSec, export_format="wav")
        spec_png = generate_mel_spectrogram_png(trimmed_path)

        # Initialize/Retrieve Job
        pipeline = AudioJobPipeline(job_id)
        job_id = pipeline.initialize_job(original_path) # Ensure input.wav exists in job folder

        import json
        musical_context = ""
        final_bpm = bpm
        final_chords = []
        
        if mode == "producer":
            if chords:
                try:
                    final_chords = json.loads(chords)
                except json.JSONDecodeError:
                    final_chords = []
            
            if not final_bpm or not final_chords:
                detected_bpm, beat_times = detect_tempo(trimmed_path)
                raw_chords = extract_chords(trimmed_path)
                
                if not final_bpm:
                    final_bpm = detected_bpm
                if not final_chords:
                    final_chords = chords_to_beats(raw_chords, detected_bpm)
            
            if final_chords and final_bpm:
                musical_context = format_chords_for_llm(final_chords, final_bpm)
        
        enhanced_prompt = f"{musical_context}\n\n{prompt}" if musical_context else prompt

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

        if advice is None:
            raise Exception("AI Model returned no response. Check API Key and Model ID.")

        midi_output_dir = os.path.join(BASE_JOBS_DIR, "chat_midi")
        clean_advice, midi_filename = extract_and_generate_midi(advice, output_dir=midi_output_dir)
        
        clean_advice, dsp_actions = extract_dsp_actions(clean_advice)

        midi_url = f"/audio_jobs/chat_midi/{midi_filename}" if midi_filename else None

        print(f"📝 Saving analysis advice for job {job_id}...")
        pipeline.save_analysis(clean_advice)

        print(f"✅ Analysis for job {job_id} complete. Returning response.")
        return {
            "sessionId": session_id,
            "job_id": job_id,
            "advice": clean_advice,
            "spectrogramPngBase64": base64.b64encode(spec_png).decode("utf-8"),
            "midiDownloadUrl": midi_url,
            "dspActions": dsp_actions,
            "bpm": final_bpm,
            "chords": final_chords,
        }
    except Exception as e:
        print(f"Error in analyze endpoint: {e}")
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

    # Parse and extract MIDI if the AI generated any
    midi_output_dir = os.path.join(BASE_JOBS_DIR, "chat_midi")
    clean_reply, midi_filename = extract_and_generate_midi(reply, output_dir=midi_output_dir)
    
    clean_reply, dsp_actions = extract_dsp_actions(clean_reply)
    
    midi_url = None
    if midi_filename:
        # Return a relative path for the frontend to append to the base URL
        midi_url = f"/audio_jobs/chat_midi/{midi_filename}"

    # If we have a jobId, save this follow-up advice
    if jobId:
        pipeline = AudioJobPipeline(jobId)
        # Append to advice instead of overwriting, or save as a separate follow-up
        advice_path = os.path.join(pipeline.analysis_dir, "advice.txt")
        with open(advice_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- Follow-up ---\nUser: {message}\nAI: {clean_reply}")

    return {
        "reply": clean_reply,
        "midiDownloadUrl": midi_url,
        "dspActions": dsp_actions
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

