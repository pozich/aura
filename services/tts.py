import os
from pathlib import Path
from google.genai import types
from dotenv import load_dotenv

from services.gemini_client import get_client

OUTPUT_PATH = Path(__file__).parent.parent / "tts_test.wav"
load_dotenv()


def synthesize(text: str, voice: str = "Charon") -> bytes:
    client = get_client()
    tts_model = os.environ.get("GEMINI_TTS_MODEL")
    if not tts_model:
        raise RuntimeError("GEMINI_TTS_M0DEL not found!")
    response = client.models.generate_content(
        model=tts_model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    return response.candidates[0].content.parts[0].inline_data.data


if __name__ == "__main__":
    audio_bytes = synthesize(
        "Сознание всегда начинает с того, что уже дано ему в представлении."
    )
    OUTPUT_PATH.write_bytes(audio_bytes)
    print(f"saved: {OUTPUT_PATH}")
