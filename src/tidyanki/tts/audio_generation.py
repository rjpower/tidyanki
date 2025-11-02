from dataclasses import dataclass

from google.cloud import texttospeech
from google.oauth2 import service_account

from tidyanki.config import settings
from tidyanki.config.languages import Language


@dataclass
class TTSAudio:
    """Represents generated text-to-speech audio data"""

    text: str
    data: bytes


def generate_tts_audio(text: str, language: Language) -> TTSAudio | None:
    """Generate TTS audio for text using Google Cloud Text-to-Speech API

    Uses Google service account credentials from settings.
    """
    if not language.tts_language_code or not language.tts_voice_name:
        return None

    if not settings.GOOGLE_SERVICE_ACCOUNT_INFO:
        print("Warning: GOOGLE_SERVICE_ACCOUNT_INFO not configured, skipping TTS")
        return None

    credentials = service_account.Credentials.from_service_account_info(
        settings.GOOGLE_SERVICE_ACCOUNT_INFO
    )
    tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language.tts_language_code,
        name=language.tts_voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.8,
        pitch=0.0,
    )

    synthesis_input = texttospeech.SynthesisInput(text=text)

    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return TTSAudio(text=text, data=response.audio_content)
    except Exception as e:
        print(f"Google TTS API error for text '{text}': {str(e)}")
        return None
