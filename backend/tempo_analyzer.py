"""
Tempo/BPM detection using librosa.
"""

import librosa
import numpy as np
from typing import Tuple, List


def detect_tempo(audio_path: str) -> Tuple[float, List[float]]:
    """
    Detect tempo (BPM) and beat positions from audio file.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Tuple of (bpm, beat_times) where beat_times is list of beat positions in seconds
    """
    # Load audio
    y, sr = librosa.load(audio_path, sr=None)
    
    # Detect tempo and beat frames
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    
    # Convert tempo to float if it's an array
    if isinstance(tempo, np.ndarray):
        bpm = float(tempo[0]) if len(tempo) > 0 else 120.0
    else:
        bpm = float(tempo)
    
    # Convert beat frames to times
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    
    return bpm, beat_times


def seconds_to_beats(seconds: float, bpm: float) -> float:
    """Convert seconds to beats given a BPM."""
    beats_per_second = bpm / 60.0
    return seconds * beats_per_second


def beats_to_seconds(beats: float, bpm: float) -> float:
    """Convert beats to seconds given a BPM."""
    seconds_per_beat = 60.0 / bpm
    return beats * seconds_per_beat
