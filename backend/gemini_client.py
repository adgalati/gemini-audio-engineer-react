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

# Singleton client instance - keeps httpx connection alive across sessions
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Get or create a singleton Gemini client instance."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing GEMINI_API_KEY. Create backend/.env with:\n\n"
                "GEMINI_API_KEY=YOUR_KEY_HERE\n"
            )
        _client = genai.Client(api_key=api_key)
    return _client


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

    print(f"Uploading file: {audio_path}...")
    uploaded_audio = client.files.upload(file=audio_path)

    print(f"File uploaded: {uploaded_audio.name}. Waiting for processing...")
    while True:
        # We must fetch the file again to get the updated state
        uploaded_audio = client.files.get(name=uploaded_audio.name)
        
        # Check state (handles 'PROCESSING', 'ACTIVE', 'FAILED')
        state = uploaded_audio.state.name.upper() if hasattr(uploaded_audio.state, 'name') else str(uploaded_audio.state).upper()
        
        if state == "ACTIVE":
            print("Audio processing complete. File is ACTIVE.")
            break
        elif state == "FAILED":
            raise ValueError(f"Google failed to process the audio file. State: {state}")
        
        # Wait 1 second before checking again
        time.sleep(1)

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
        message=[user_prompt, uploaded_audio, spectrogram_part]
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

