import os
import time
import uuid
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import get_system_prompt

load_dotenv()

# In-memory storage for active chat sessions
# Dict[str, genai.chats.Chat]
_sessions: Dict[str, object] = {}

# Cached client and key
_client: Optional[genai.Client] = None
_cached_api_key: Optional[str] = None


def _get_client() -> genai.Client:
    """Get or create a Gemini client instance, updating if API key changes."""
    global _client, _cached_api_key
    load_dotenv(override=True)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise RuntimeError(
            "Missing or placeholder GEMINI_API_KEY. Update backend/.env with a valid key."
        )
        
    if _client is None or _cached_api_key != api_key:
        print("Initializing AI Studio client using API Key (with extended timeout)")
        _client = genai.Client(api_key=api_key, http_options={'timeout': 300000})
        _cached_api_key = api_key
        
    return _client


def _get_audio_part(client: genai.Client, audio_path: str) -> types.Part:
    """Loads audio as inline Part first to avoid File API policy restrictions, falling back to Files API."""
    ext = os.path.splitext(audio_path)[1].lower()
    mime_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mp3",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".m4a": "audio/m4a",
        ".aac": "audio/aac",
    }
    mime_type = mime_map.get(ext, "audio/wav")

    # 1. Prefer inline bytes: works with all API keys/policies, no separate upload request
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        print(f"Loading inline audio: {len(audio_bytes)} bytes ({mime_type})")
        return types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    except Exception as e:
        print(f"Inline audio read exception: {e}")

    # 2. Fallback to Files API if local read failed
    print(f"Uploading file via Files API: {audio_path}...")
    uploaded_audio = client.files.upload(file=audio_path)

    print(f"File uploaded: {uploaded_audio.name}. Waiting for processing...")
    while True:
        uploaded_audio = client.files.get(name=uploaded_audio.name)
        state = uploaded_audio.state.name.upper() if hasattr(uploaded_audio.state, 'name') else str(uploaded_audio.state).upper()
        if state == "ACTIVE":
            print("Audio processing complete. File is ACTIVE.")
            break
        elif state == "FAILED":
            raise ValueError(f"Google failed to process the audio file. State: {state}")
        time.sleep(1)

    return types.Part.from_uri(
        file_uri=uploaded_audio.uri,
        mime_type=uploaded_audio.mime_type or mime_type,
    )


def start_audio_chat_session(
    audio_path: str,
    spectrogram_png_bytes: bytes,
    user_prompt: str,
    model_id: str,
    temperature: float = 0.2,
    thinking_budget: Optional[int] = None,
    mode: str = "engineer",
) -> Tuple[str, str]:
    """
    Starts a new chat session with the audio context.
    Returns (session_id, initial_response_text).
    """
    client = _get_client()

    audio_part = _get_audio_part(client, audio_path)

    spectrogram_part = types.Part.from_bytes(
        data=spectrogram_png_bytes,
        mime_type="image/png",
    )


    # Configure Thinking if requested (assuming model supports it)
    # Note: 'thinking_config' is strictly for models that support it (e.g. gemini-2.0-flash-thinking-exp)
    # Start with standard config
    config_args = {
        "system_instruction": get_system_prompt(mode),
        "temperature": temperature,
    }
    
    if thinking_budget and thinking_budget > 0:
        # If thinking is enabled, we might need to adjust config structure depending on SDK version
        # For this starter, we'll pass it if the user provides it, assuming a compatible model.
        config_args["thinking_config"] = {"include_thoughts": True}

    chat = client.chats.create(
        model=model_id,
        config=types.GenerateContentConfig(**config_args),
    )
    print(f"Sending request to model: {model_id}...")

    # Send initial message with context
    response = chat.send_message(
        message=[user_prompt, audio_part, spectrogram_part]
    )


    session_id = str(uuid.uuid4())
    _sessions[session_id] = chat

    return session_id, response.text


def send_chat_message(session_id: str, user_message: str) -> str:
    """
    Sends a follow-up message to an existing session.
    """
    chat = _sessions.get(session_id)
    if not chat:
        raise ValueError("Session not found or expired.")

    response = chat.send_message(message=user_message)
    return response.text

def validate_midi_with_gemini(midi_summaries: str) -> str:
    """
    Prompts Gemini to validate the musicality of the extracted MIDI summaries.
    Returns the model's critique and suggested corrections.
    """
    client = _get_client()
    
    prompt = f"""
    You are a professional music theory expert and arranger.
    I have extracted MIDI data from stems of a song.
    
    Below are the summaries of these MIDI files (note ranges, density, and samples).
    Please analyze them for:
    1. Pitch outliers (notes that seem far outside the expected range for the instrument).
    2. Rhythm consistency (unusual gaps or overlaps).
    3. Harmonic alignment (do these instruments seem to be in the same key?).
    
    MIDI Summaries:
    {midi_summaries}
    
    Reply with a concise critique and specific suggested corrections (e.g., 'Transpose Bass down 1 octave').
    """
    
    # We use a generate call with model fallbacks
    for model_name in ["gemini-3.6-flash", "gemini-1.5-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text
        except Exception:
            continue
    raise RuntimeError("Could not connect to Gemini models for MIDI validation.")
