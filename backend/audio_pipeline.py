import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Constants
BASE_JOBS_DIR = os.path.join(os.path.dirname(__file__), "static", "jobs")


class AudioJobPipeline:
    """
    Manages the lifecycle of an audio processing job.
    Structure:
    audio_jobs/<job_id>/
        input.wav
        status.json
        stems/
        midi/
    """

    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id or str(uuid.uuid4())
        self.job_dir = os.path.join(BASE_JOBS_DIR, self.job_id)
        self.stems_dir = os.path.join(self.job_dir, "stems")
        self.midi_dir = os.path.join(self.job_dir, "midi")
        self.status_path = os.path.join(self.job_dir, "status.json")

    def initialize_job(self, input_audio_path: str) -> str:
        """Create job directory structure and store input file."""
        os.makedirs(self.job_dir, exist_ok=True)
        os.makedirs(self.stems_dir, exist_ok=True)
        os.makedirs(self.midi_dir, exist_ok=True)

        # Copy input file to job directory
        dest_input = os.path.join(self.job_dir, "input.wav")
        shutil.copy(input_audio_path, dest_input)

        self.update_status("initialized", progress=0)
        return self.job_id

    def update_status(self, state: str, progress: int = 0, message: str = "", error: Optional[str] = None):
        """Update status.json with current progress."""
        status = {
            "job_id": self.job_id,
            "state": state, # initialized, processing_stems, processing_midi, success, failed
            "progress": progress,
            "message": message,
            "error": error,
            "updated_at": datetime.now().isoformat(),
            "artifacts": {
                "stems": [f for f in os.listdir(self.stems_dir)] if os.path.exists(self.stems_dir) else [],
                "midi": [f for f in os.listdir(self.midi_dir)] if os.path.exists(self.midi_dir) else []
            }
        }
        with open(self.status_path, "w") as f:
            json.dump(status, f, indent=4)

    def get_status(self) -> Dict[str, Any]:
        """Read the current status.json."""
        if not os.path.exists(self.status_path):
            return {"error": "Job not found"}
        with open(self.status_path, "r") as f:
            return json.load(f)

from midi_engine import extract_midi_from_audio

def start_processing_pipeline(job_id: str):
    """
    The main background task function.
    """
    pipeline = AudioJobPipeline(job_id)
    try:
        pipeline.update_status("processing_stems", progress=10, message="Starting initial stem separation (Demucs)...")
        
        input_wav = os.path.join(pipeline.job_dir, "input.wav")
        # 1. Core separation (4 stems)
        separate_stems_demucs(input_wav, pipeline.job_dir)
        
        # Flatten Demucs output
        model_name = "htdemucs"
        filename_no_ext = os.path.splitext(os.path.basename(input_wav))[0]
        demucs_out_base = os.path.join(pipeline.job_dir, model_name, filename_no_ext)
        
        if os.path.exists(demucs_out_base):
            for stem_file in os.listdir(demucs_out_base):
                shutil.move(os.path.join(demucs_out_base, stem_file), os.path.join(pipeline.stems_dir, stem_file))
            shutil.rmtree(os.path.join(pipeline.job_dir, model_name))

        # 2. Deep Refinement (Local splits)
        pipeline.update_status("processing_stems", progress=30, message="Refining stems (Vocals, Drums, Instruments)...")
        
        # Vocals -> Lead / Backing
        vocals_path = os.path.join(pipeline.stems_dir, "vocals.wav")
        if os.path.exists(vocals_path):
            split_vocals_basic(vocals_path, pipeline.stems_dir)
            os.remove(vocals_path)

        # Drums -> Kick / Snare / Hats
        drums_path = os.path.join(pipeline.stems_dir, "drums.wav")
        if os.path.exists(drums_path):
            split_drums_basic(drums_path, pipeline.stems_dir)
            os.remove(drums_path)

        # Other -> Guitars / Keys / Harmony
        other_path = os.path.join(pipeline.stems_dir, "other.wav")
        if os.path.exists(other_path):
            split_other_basic(other_path, pipeline.stems_dir)
            os.remove(other_path)

        # 3. MIDI Extraction
        pipeline.update_status("processing_midi", progress=60, message="Extracting structured MIDI data from stems...")
        
        # MIDI Mapping: Stem File -> MIDI File Name
        midi_map = {
            "vocals_lead.wav": "melody_lead.mid",
            "bass.wav": "bass.mid",
            "guitars.wav": "guitars.mid",
            "keys_synth.wav": "keys_synth.mid",
            "harmony.wav": "harmony.mid",
            "snare.wav": "drums_notes.mid" # basic-pitch doesn't do drums well, but we'll try snare for energy
        }
        
        for i, (stem_name, midi_name) in enumerate(midi_map.items()):
            stem_path = os.path.join(pipeline.stems_dir, stem_name)
            if os.path.exists(stem_path):
                pipeline.update_status(
                    "processing_midi", 
                    progress=60 + int((i/len(midi_map)) * 30), 
                    message=f"Extracting MIDI: {midi_name}..."
                )
                output_midi = os.path.join(pipeline.midi_dir, midi_name)
                try:
                    extract_midi_from_audio(stem_path, output_midi)
                except Exception as midi_err:
                    print(f"⚠️ Failed to extract MIDI for {stem_name}: {midi_err}")

        pipeline.update_status("success", progress=100, message="Processing complete. Deep stems and MIDI artifacts are ready.")
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"🔥 Pipeline Error: {error_msg}")
        pipeline.update_status("failed", error=str(e), message="An error occurred during processing.")



