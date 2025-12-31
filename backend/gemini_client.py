import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing GEMINI_API_KEY. Create backend/.env with:\n\n"
            "GEMINI_API_KEY=YOUR_KEY_HERE\n"
        )
    return genai.Client(api_key=api_key)


DEFAULT_SYSTEM_INSTRUCTION = """
You are a world-class Audio Engineer (Mixing & Mastering).

You have been provided with:
1) An audio file (listen for dynamics, tone, balance, stereo image, noise/distortion).
2) A spectrogram image of that audio (look for frequency masking, resonances, noise floor, spectral gaps).

Combine these inputs to answer the user's request.

Be technical, precise, and constructive.
Use terms like LUFS (Loudness Units relative to Full Scale), EQ curves, compression ratios, attack/release,
stereo correlation, and frequency ranges (Hz).
When suggesting EQ, provide approximate center frequencies and bandwidth/Q.
When suggesting compression, include ratio/threshold/attack/release and what you expect to hear.
""".strip()


def analyze_audio(
    audio_path: str,
    spectrogram_png_bytes: bytes,
    user_prompt: str,
    model_id: str,
    temperature: float = 0.2,
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
) -> str:
    """
    Upload audio + attach spectrogram image + send prompt to Gemini.
    Returns the model response text.
    """
    client = _get_client()

    uploaded_audio = client.files.upload(file=audio_path)

    spectrogram_part = types.Part.from_bytes(
        data=spectrogram_png_bytes,
        mime_type="image/png",
    )

    response = client.models.generate_content(
        model=model_id,
        contents=[user_prompt, uploaded_audio, spectrogram_part],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        ),
    )

    return response.text
