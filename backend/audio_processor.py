import io
import os
import tempfile
from typing import Tuple

import librosa
import librosa.display
import matplotlib
# Force non-interactive backend (Must be before importing pyplot)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch
from dotenv import load_dotenv
from pydub import AudioSegment

# Global device detection (CUDA/GPU support)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Audio Processor initialized. Using device: {DEVICE}")

# Load environment variables and configure FFmpeg path for pydub

load_dotenv()

_ffmpeg_path = os.getenv("FFMPEG_PATH")
if _ffmpeg_path and os.path.isdir(_ffmpeg_path):
    # pydub looks for ffmpeg/ffprobe executables in this directory
    AudioSegment.converter = os.path.join(_ffmpeg_path, "ffmpeg.exe")
    AudioSegment.ffprobe = os.path.join(_ffmpeg_path, "ffprobe.exe")


def trim_audio_to_temp(
    audio_path: str,
    start_sec: float,
    end_sec: float,
    export_format: str = "wav",
) -> str:
    """
    Trim an audio file to [start_sec, end_sec] and export to a temp file.

    Returns:
        path to trimmed file
    """
    audio = AudioSegment.from_file(audio_path)

    duration_sec = len(audio) / 1000.0
    start_sec = max(0.0, float(start_sec))
    end_sec = min(duration_sec, float(end_sec))

    if end_sec <= start_sec:
        end_sec = min(duration_sec, start_sec + 0.1)

    start_ms = int(start_sec * 1000)
    end_ms = int(end_sec * 1000)

    trimmed = audio[start_ms:end_ms]

    suffix = f".{export_format}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        trimmed.export(tmp.name, format=export_format)
        return tmp.name


def generate_mel_spectrogram_png(
    audio_path: str,
    n_mels: int = 128,
    fmax: int = 16000,
) -> bytes:
    """
    Generate Mel spectrogram (PNG bytes).
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    if y.size == 0:
        raise ValueError("Audio appears to be empty.")

    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, fmax=fmax)
    S_dB = librosa.power_to_db(S, ref=np.max)

    plt.figure(figsize=(10, 4))
    librosa.display.specshow(S_dB, x_axis="time", y_axis="mel", sr=sr, fmax=fmax)
    plt.colorbar(format="%+2.0f dB")
    plt.title("Mel-frequency spectrogram")
    plt.tight_layout()
import subprocess
import shutil

def separate_stems_demucs(input_path: str, output_dir: str) -> bool:
    """
    Separate audio into 4 stems (vocals, drums, bass, other) using Demucs.
    Uses htdemucs model by default.
    """
    try:
        # Construct demucs command
        # -n htdemucs: Hybrid Transformer Demucs (v4)
        # -o output_dir: Output base directory
        # --device: Use CUDA if detected
        cmd = [
            "python", "-m", "demucs",
            "--device", DEVICE,
            "-n", "htdemucs",
            "-o", output_dir,
            input_path
        ]
        
        print(f"🎬 Running Demucs: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        print("✅ Demucs separation successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Demucs failed: {e.stderr}")
        raise Exception(f"Stem separation failed: {e.stderr}")
    except Exception as e:
        print(f"❌ Unexpected error in Demucs: {e}")
        raise e


def split_vocals_basic(vocals_path: str, output_dir: str) -> Tuple[str, str]:
    """
    Split a vocals stem into lead and backing using a simple center-channel extraction.
    """
    y, sr = librosa.load(vocals_path, sr=None, mono=False)
    
    if y.ndim < 2:
        lead_path = os.path.join(output_dir, "vocals_lead.wav")
        shutil.copy(vocals_path, lead_path)
        return lead_path, vocals_path

    mid = (y[0] + y[1]) / 2.0
    side = (y[0] - y[1]) / 2.0
    
    lead_path = os.path.join(output_dir, "vocals_lead.wav")
    backing_path = os.path.join(output_dir, "vocals_backing.wav")
    
    import soundfile as sf
    sf.write(lead_path, mid, sr)
    sf.write(backing_path, side, sr)
    
    return lead_path, backing_path


def split_drums_basic(drums_path: str, output_dir: str) -> Tuple[str, str, str]:
    """
    Split drums into kick, snare, and hats using spectral filtering.
    """
    y, sr = librosa.load(drums_path, sr=None, mono=True)
    D = librosa.stft(y)
    S = np.abs(D)
    
    # Frequency bands
    freqs = librosa.fft_frequencies(sr=sr)
    
    # Kick: < 150Hz
    kick_mask = freqs < 150
    # Snare: 150Hz - 3kHz
    snare_mask = (freqs >= 150) & (freqs < 3000)
    # Hats: > 3kHz
    hats_mask = freqs >= 3000
    
    masks = [kick_mask, snare_mask, hats_mask]
    names = ["kick", "snare", "hats"]
    paths = []
    
    import soundfile as sf
    for mask, name in zip(masks, names):
        D_masked = D.copy()
        D_masked[~mask, :] = 0
        y_masked = librosa.istft(D_masked)
        out_path = os.path.join(output_dir, f"{name}.wav")
        sf.write(out_path, y_masked, sr)
        paths.append(out_path)
        
    return tuple(paths)


def split_other_basic(other_path: str, output_dir: str) -> Tuple[str, str, str]:
    """
    Split the 'other' stem into guitars, keys, and harmony using similar spectral bands.
    """
    y, sr = librosa.load(other_path, sr=None, mono=True)
    D = librosa.stft(y)
    
    freqs = librosa.fft_frequencies(sr=sr)
    
    # Harmony (Low-mids): 100Hz - 500Hz
    harmony_mask = (freqs >= 100) & (freqs < 500)
    # Guitars (Mids): 500Hz - 2.5kHz
    guitars_mask = (freqs >= 500) & (freqs < 2500)
    # Keys/Synth (Highs): > 2.5kHz
    keys_mask = freqs >= 2500
    
    masks = [harmony_mask, guitars_mask, keys_mask]
    names = ["harmony", "guitars", "keys_synth"]
    paths = []
    
    import soundfile as sf
    for mask, name in zip(masks, names):
        D_masked = D.copy()
        D_masked[~mask, :] = 0
        y_masked = librosa.istft(D_masked)
        out_path = os.path.join(output_dir, f"{name}.wav")
        sf.write(out_path, y_masked, sr)
        paths.append(out_path)
        
    return tuple(paths)

