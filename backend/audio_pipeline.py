import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Constants
BASE_JOBS_DIR = os.path.join(os.path.dirname(__file__), "audio_jobs")

print(f"🛤️ BASE_JOBS_DIR resolved to: {BASE_JOBS_DIR}")
print(f"📍 Current Working Directory: {os.getcwd()}")


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
        if job_id in ["undefined", "null", "None", ""]:
            job_id = None
        self.job_id = (job_id or str(uuid.uuid4())).strip()
        self.job_dir = os.path.join(BASE_JOBS_DIR, self.job_id)
        self.stems_dir = os.path.join(self.job_dir, "stems")
        self.midi_dir = os.path.join(self.job_dir, "midi")
        self.analysis_dir = os.path.join(self.job_dir, "analysis")
        self.status_path = os.path.join(self.job_dir, "status.json")
        print(f"🏗️ Pipeline initialized for Job: {self.job_id}")
        print(f"📁 Target Job Directory: {self.job_dir}")
        print(f"📝 Target Status Path: {self.status_path}")


    def initialize_job(self, input_audio_path: str) -> str:
        """Create job directory structure and store input file."""
        print(f"📦 Initializing job {self.job_id} in {self.job_dir}")
        os.makedirs(self.job_dir, exist_ok=True)
        os.makedirs(self.stems_dir, exist_ok=True)
        os.makedirs(self.midi_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

        dest_input = os.path.join(self.job_dir, "input.wav")
        # ONLY copy and reset status if it's a NEW job or input is missing
        if not os.path.exists(dest_input):
            print(f"📥 Copying input file for the first time: {dest_input}")
            shutil.copy(input_audio_path, dest_input)
        else:
            print(f"🔄 Job {self.job_id} already exists. Skipping input copy.")

        return self.job_id

    @property
    def midi_output_dir(self) -> str:
        return self.midi_dir

    def update_status(self, state: str, progress: int = 0, message: str = "", error: Optional[str] = None):
        """Update status.json with current progress."""
        # PREVENT status reset to 0 if we are already at success or middle of processing
        # unless explicitly requested or starting a new phase.
        
        # Check current status first
        try:
            if os.path.exists(self.status_path):
                with open(self.status_path, "r") as f:
                    curr = json.load(f)
                    # If we are starting 'processing_stems' but we were already 'success', 
                    # we ALLOW it because it's a new pipeline run.
                    # But if we are 'initialized' and progress is 0, we don't overwrite success.
                    if state == "initialized" and curr.get("state") == "success":
                        print("🚫 Skipping reset to initialized as job is already successful.")
                        return
        except:
            pass

        status = {
            "job_id": self.job_id,
            "state": state, # initialized, processing_stems, processing_midi, success, failed
            "progress": progress,
            "message": message,
            "error": error,
            "updated_at": datetime.now().isoformat(),
            "artifacts": {
                "stems": [f for f in os.listdir(self.stems_dir)] if os.path.exists(self.stems_dir) else [],
                "midi": [f for f in os.listdir(self.midi_dir)] if os.path.exists(self.midi_dir) else [],
                "analysis": [f for f in os.listdir(self.analysis_dir)] if os.path.exists(self.analysis_dir) else []
            }
        }
        with open(self.status_path, "w") as f:
            json.dump(status, f, indent=4)

    def save_analysis(self, advice_text: str):
        """Save AI mixing advice to the analysis directory."""
        os.makedirs(self.analysis_dir, exist_ok=True)
        advice_path = os.path.join(self.analysis_dir, "advice.txt")
        with open(advice_path, "w", encoding="utf-8") as f:
            f.write(advice_text)
        print(f"📄 Analysis saved to: {advice_path}")

    def get_status(self) -> Dict[str, Any]:
        """Read the current status.json."""
        if not os.path.exists(self.status_path): 
            return {"error": "Job not found"}
        with open(self.status_path, "r") as f:
            return json.load(f)


from reaper_engine import generate_reaper_project
from audio_processor import (
    separate_stems_demucs, 
    separate_stems_umx, 
    split_vocals_basic, 
    split_drums_basic, 
    split_other_basic
)
from midi_engine import extract_midi_from_audio, summarize_midi_file
from gemini_client import validate_midi_with_gemini

def _move_umx_stems(output_dir: str, stems_dir: str):
    """
    Open-Unmix saves stems in a subfolder named after the input file. 
    If input is input.wav, the folder is 'input'.
    """
    umx_out_dir = os.path.join(output_dir, "input")
    if not os.path.exists(umx_out_dir):
        # Fallback to direct output_dir if UMX behavior changes
        umx_out_dir = output_dir

    print(f"📦 Moving UMX stems from {umx_out_dir} to {stems_dir}")
    found_any = False
    for stem in ["vocals.wav", "drums.wav", "bass.wav", "other.wav"]:
        src = os.path.join(umx_out_dir, stem)
        if os.path.exists(src):
            print(f"✅ Found stem: {src}")
            shutil.move(src, os.path.join(stems_dir, stem))
            found_any = True
        else:
            print(f"⚠️ UMX Stem NOT FOUND: {src}")
    
    if not found_any:
        print(f"🔥 CRITICAL: No stems were moved from {umx_out_dir}")

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
                pipeline.update_status("processing_stems", progress=20, message="Separation successful. Organizing stems...")
                _move_umx_stems(pipeline.job_dir, pipeline.stems_dir)
                success = True
            except Exception as e:
                print(f"⚠️ UMX failed, falling back to Demucs: {e}")
                separation_model = "demucs" # Fallback
        
        if separation_model == "demucs" or not success:
            separate_stems_demucs(input_wav, pipeline.job_dir)
            pipeline.update_status("processing_stems", progress=20, message="Separation successful. Organizing stems...")
            
            # Flatten Demucs output: htdemucs/input/bases.wav etc.
            model_name = "htdemucs"
            demucs_out_base = os.path.join(pipeline.job_dir, model_name, "input")
            
            if os.path.exists(demucs_out_base):
                print(f"📦 Moving Demucs stems from {demucs_out_base} to {pipeline.stems_dir}")
                for stem_file in os.listdir(demucs_out_base):
                    shutil.move(os.path.join(demucs_out_base, stem_file), os.path.join(pipeline.stems_dir, stem_file))
                
                # Cleanup model-specific folder
                shutil.rmtree(os.path.join(pipeline.job_dir, model_name))
            else:
                print(f"⚠️ Demucs output folder NOT FOUND: {demucs_out_base}")
            success = True

        # 2. Deep Refinement (Local splits)
        pipeline.update_status("processing_stems", progress=30, message="Refining stems: Splitting Vocals...")
        
        # Vocals -> Lead / Backing
        vocals_path = os.path.join(pipeline.stems_dir, "vocals.wav")
        if os.path.exists(vocals_path):
            split_vocals_basic(vocals_path, pipeline.stems_dir)
            os.remove(vocals_path)

        pipeline.update_status("processing_stems", progress=40, message="Refining stems: Splitting Drums...")
        # Drums -> Kick / Snare / Hats
        drums_path = os.path.join(pipeline.stems_dir, "drums.wav")
        if os.path.exists(drums_path):
            split_drums_basic(drums_path, pipeline.stems_dir)
            os.remove(drums_path)

        pipeline.update_status("processing_stems", progress=50, message="Refining stems: Splitting Instruments...")
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




