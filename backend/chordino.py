"""
Chordino chord extraction using Sonic Annotator with the NNLS Chroma VAMP plugin.
"""

import csv
import os
import subprocess
import tempfile
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


def get_sonic_annotator_path() -> str:
    """Get path to sonic-annotator executable from environment."""
    path = os.getenv("SONIC_ANNOTATOR_EXE")
    if not path or not os.path.exists(path):
        raise RuntimeError(
            "SONIC_ANNOTATOR_EXE not set or does not exist. "
            "Set it in backend/.env"
        )
    return path


def get_vamp_path() -> str:
    """Get VAMP plugin path from environment."""
    path = os.getenv("VAMP_PATH")
    if not path or not os.path.exists(path):
        raise RuntimeError(
            "VAMP_PATH not set or does not exist. "
            "Set it in backend/.env"
        )
    return path


def extract_chords(audio_path: str) -> List[Dict]:
    """
    Extract chord progression from audio using Chordino VAMP plugin.
    
    Args:
        audio_path: Path to audio file (WAV recommended)
        
    Returns:
        List of chord dicts: [{"time": float, "duration": float, "chord": str}, ...]
    """
    sonic_annotator = get_sonic_annotator_path()
    vamp_path = get_vamp_path()
    
    # Create temp directory for output
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Set VAMP_PATH environment for plugin discovery
        env = os.environ.copy()
        env["VAMP_PATH"] = vamp_path
        
        # Run sonic-annotator with Chordino
        # Using simplechord output (chord labels with timestamps)
        # Note: sonic-annotator outputs to same dir as input or uses --csv-basedir
        cmd = [
            sonic_annotator,
            "-d", "vamp:nnls-chroma:chordino:simplechord",
            "-w", "csv",
            "--csv-basedir", temp_dir,
            "--csv-force",
            audio_path
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            print(f"Sonic Annotator error: {result.stderr}")
            return []
        
        # Find the output CSV file (sonic-annotator creates filename based on input)
        csv_files = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
        if not csv_files:
            print("No CSV output found from Sonic Annotator")
            return []
        
        output_path = os.path.join(temp_dir, csv_files[0])
        
        # Parse CSV output
        chords = parse_chord_csv(output_path)
        return chords
        
    except subprocess.TimeoutExpired:
        print("Chord extraction timed out")
        return []
    except Exception as e:
        print(f"Chord extraction error: {e}")
        return []
    finally:
        # Clean up temp directory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def parse_chord_csv(csv_path: str) -> List[Dict]:
    """
    Parse Sonic Annotator CSV output to chord list.
    
    CSV format: timestamp, duration, chord_label
    """
    chords = []
    
    if not os.path.exists(csv_path):
        return chords
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            for i, row in enumerate(rows):
                if len(row) < 2:
                    continue
                    
                try:
                    time = float(row[0])
                    chord = row[1].strip() if len(row) > 1 else "N"
                    
                    # Calculate duration (time until next chord)
                    if i + 1 < len(rows) and len(rows[i + 1]) >= 1:
                        next_time = float(rows[i + 1][0])
                        duration = next_time - time
                    else:
                        # Last chord - estimate 4 beats at 120 BPM = 2 seconds
                        duration = 2.0
                    
                    # Skip "N" (no chord) entries that are very short
                    if chord == "N" and duration < 0.5:
                        continue
                    
                    chords.append({
                        "time": time,
                        "duration": duration,
                        "chord": chord
                    })
                except (ValueError, IndexError):
                    continue
                    
    except Exception as e:
        print(f"Error parsing chord CSV: {e}")
    
    return chords


def chords_to_beats(chords: List[Dict], bpm: float) -> List[Dict]:
    """
    Convert time-based chords to beat-based format.
    
    Args:
        chords: List of {"time": float, "duration": float, "chord": str}
        bpm: Tempo in BPM
        
    Returns:
        List of {"chord": str, "start_beat": float, "duration_beats": float}
    """
    beats_per_second = bpm / 60.0
    
    return [
        {
            "chord": c["chord"],
            "start_beat": round(c["time"] * beats_per_second, 2),
            "duration_beats": round(c["duration"] * beats_per_second, 2)
        }
        for c in chords
    ]


def format_chords_for_llm(chords: List[Dict], bpm: float) -> str:
    """
    Format chord data as text context for LLM.
    
    Args:
        chords: Beat-based chord list
        bpm: Tempo in BPM
        
    Returns:
        Formatted string for LLM context
    """
    if not chords:
        return ""
    
    lines = [
        "[MUSICAL CONTEXT]",
        f"Tempo: {round(bpm)} BPM",
        "Detected Chords:"
    ]
    
    for c in chords:
        start = c["start_beat"]
        end = start + c["duration_beats"]
        lines.append(f"- {c['chord']}: beats {start:.1f}-{end:.1f}")
    
    return "\n".join(lines)
