import io
import tempfile
from typing import Tuple

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment


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
    fmax: int = 8000,
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

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=160)
    buf.seek(0)
    plt.close()
    return buf.getvalue()
