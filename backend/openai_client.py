import os
import base64
import uuid
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# In-memory storage for active chat sessions
# Each session stores: {"client": OpenAI, "messages": list, "model": str}
_sessions: Dict[str, dict] = {}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Update backend/.env with your OpenAI API key."
        )
    return OpenAI(api_key=api_key)


DEFAULT_SYSTEM_INSTRUCTION = """
You are a world-class Audio Engineer (Mixing & Mastering).

You have been provided with an audio file, and a prompt from the user with the style they are going for and the direction they want to go in.
Listen carefully for dynamics, tone, balance, stereo image, and any noise or distortion.

Be technical, precise, and constructive, providing evidence from the audio file to support your recommendations.
""".strip()


def _get_audio_mime_type(audio_path: str) -> str:
    """Determine MIME type based on file extension."""
    ext = os.path.splitext(audio_path)[1].lower()
    mime_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }
    return mime_map.get(ext, "audio/wav")


def start_audio_chat_session(
    audio_path: str,
    spectrogram_png_bytes: bytes,  # Not used for OpenAI, kept for API compatibility
    user_prompt: str,
    model_id: str = "gpt-audio",
    temperature: float = 0.2,
    thinking_budget: Optional[int] = None,  # Not used for OpenAI, kept for API compatibility
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
) -> Tuple[str, str]:
    """
    Starts a new chat session with audio context using OpenAI.
    Returns (session_id, initial_response_text).
    Note: gpt-audio does not support image input, so spectrogram is not sent.
    """
    client = _get_client()

    # Encode audio as base64
    with open(audio_path, "rb") as f:
        audio_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    audio_mime = _get_audio_mime_type(audio_path)

    # Build message with audio only (gpt-audio does not support images)
    messages = [
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_data,
                        "format": audio_mime.split("/")[-1],  # e.g., "wav", "mpeg", "flac"
                    }
                },
                {
                    "type": "text",
                    "text": user_prompt
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
    )

    assistant_message = response.choices[0].message.content

    # Store session for follow-up messages
    session_id = str(uuid.uuid4())
    messages.append({"role": "assistant", "content": assistant_message})
    
    _sessions[session_id] = {
        "client": client,
        "messages": messages,
        "model": model_id,
        "temperature": temperature,
    }

    return session_id, assistant_message


def send_chat_message(session_id: str, user_message: str) -> str:
    """
    Sends a follow-up message to an existing session.
    """
    session = _sessions.get(session_id)
    if not session:
        raise ValueError("Session not found or expired.")

    session["messages"].append({"role": "user", "content": user_message})

    response = session["client"].chat.completions.create(
        model=session["model"],
        messages=session["messages"],
        temperature=session["temperature"],
    )

    assistant_message = response.choices[0].message.content
    session["messages"].append({"role": "assistant", "content": assistant_message})

    return assistant_message
