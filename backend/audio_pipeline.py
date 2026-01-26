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

from reaper_engine import generate_reaper_project

def start_processing_pipeline(job_id: str, separation_model: str = "demucs"):
    """
    The main background task function.
    """
    pipeline = AudioJobPipeline(job_id)
    try:
        pipeline.update_status("processing_stems", progress=10, message=f"Starting stem separation ({separation_model})...")
        
        input_wav = os.path.join(pipeline.job_dir, "input.wav")
        success = False
        
        # 1. Core separation (4 stems)
        if separation_model == "umx":
            try:
                separate_stems_umx(input_wav, pipeline.job_dir)
                _move_umx_stems(pipeline.job_dir, pipeline.stems_dir)
                success = True
            except Exception as e:
                print(f"⚠️ UMX failed, falling back to Demucs: {e}")
                separation_model = "demucs" # Fallback
        
        if separation_model == "demucs" or not success:
            separate_stems_demucs(input_wav, pipeline.job_dir)
            
            # Flatten Demucs output
            model_name = "htdemucs"
            filename_no_ext = os.path.splitext(os.path.basename(input_wav))[0]
            demucs_out_base = os.path.join(pipeline.job_dir, model_name, filename_no_ext)
            
            if os.path.exists(demucs_out_base):
                for stem_file in os.listdir(demucs_out_base):
                    shutil.move(os.path.join(demucs_out_base, stem_file), os.path.join(pipeline.stems_dir, stem_file))
                shutil.rmtree(os.path.join(pipeline.job_dir, model_name))
            success = True


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
            "snare.wav": "drums_notes.mid" 
        }
        
        midi_summaries = []
        midi_files_found = []
        for i, (stem_name, midi_name) in enumerate(midi_map.items()):
            stem_path = os.path.join(pipeline.stems_dir, stem_name)
            if os.path.exists(stem_path):
                pipeline.update_status(
                    "processing_midi", 
                    progress=60 + int((i/len(midi_map)) * 20), 
                    message=f"Extracting MIDI: {midi_name}..."
                )
                output_midi = os.path.join(pipeline.midi_dir, midi_name)
                try:
                    extract_midi_from_audio(stem_path, output_midi)
                    midi_files_found.append(midi_name)
                    # For Phase 2B: Validation
                    summary = summarize_midi_file(output_midi)
                    midi_summaries.append(summary)
                except Exception as midi_err:
                    print(f"⚠️ Failed to extract MIDI for {stem_name}: {midi_err}")

        # 4. MIDI Validation (Phase 2B)
        if midi_summaries:
            pipeline.update_status("processing_midi", progress=85, message="Validating MIDI correctness with Gemini...")
            validation_report = validate_midi_with_gemini("\n\n".join(midi_summaries))
            
            # Store validation report in status.json
            current_status = pipeline.get_status()
            current_status["validation_report"] = validation_report
            with open(pipeline.status_path, "w") as f:
                json.dump(current_status, f, indent=4)

        # 5. REAPER Project Generation (Phase 2C)
        pipeline.update_status("success", progress=95, message="Generating REAPER Project File...")
        stems_found = os.listdir(pipeline.stems_dir)
        rpp_name = f"Project_{job_id[:8]}.RPP"
        rpp_path = os.path.join(pipeline.job_dir, rpp_name)
        generate_reaper_project(job_id, stems_found, midi_files_found, rpp_path)
        
        # Update artifacts in status.json to index RPP
        current_status = pipeline.get_status()
        current_status["artifacts"]["project"] = [rpp_name]
        with open(pipeline.status_path, "w") as f:
            json.dump(current_status, f, indent=4)

        pipeline.update_status("success", progress=100, message="Processing complete. Deep stems, MIDI, and REAPER Project are ready.")
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"🔥 Pipeline Error: {error_msg}")
        pipeline.update_status("failed", error=str(e), message="An error occurred during processing.")

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"🔥 Pipeline Error: {error_msg}")
        pipeline.update_status("failed", error=str(e), message="An error occurred during processing.")




