from pydantic import BaseModel


class Language(BaseModel):
    abbreviation: str
    name: str
    tts_language_code: str | None = None  # For Google TTS
    tts_voice_name: str | None = None  # For Google TTS


LANGUAGES = {
    lang.abbreviation: lang
    for lang in [
        Language(
            abbreviation="en",
            name="English",
            tts_language_code="en-US",
            tts_voice_name="en-US-Neural2-C",
        ),
        Language(
            abbreviation="ja",
            name="Japanese",
            tts_language_code="ja-JP",
            tts_voice_name="ja-JP-Neural2-D",
        ),
        Language(
            abbreviation="es",
            name="Spanish",
            tts_language_code="es-ES",
            tts_voice_name="es-ES-Neural2-A",
        ),
        Language(
            abbreviation="fr",
            name="French",
            tts_language_code="fr-FR",
            tts_voice_name="fr-FR-Neural2-A",
        ),
        Language(
            abbreviation="de",
            name="German",
            tts_language_code="de-DE",
            tts_voice_name="de-DE-Neural2-A",
        ),
        Language(
            abbreviation="it",
            name="Italian",
            tts_language_code="it-IT",
            tts_voice_name="it-IT-Neural2-A",
        ),
        Language(
            abbreviation="zh",
            name="Chinese",
            tts_language_code="cmn-CN",
            tts_voice_name="cmn-CN-Neural2-A",
        ),
        Language(
            abbreviation="ko",
            name="Korean",
            tts_language_code="ko-KR",
            tts_voice_name="ko-KR-Neural2-A",
        ),
        Language(
            abbreviation="ru",
            name="Russian",
            tts_language_code="ru-RU",
            tts_voice_name="ru-RU-Neural2-A",
        ),
        Language(
            abbreviation="pt",
            name="Portuguese",
            tts_language_code="pt-BR",
            tts_voice_name="pt-BR-Neural2-A",
        ),
        Language(
            abbreviation="ar",
            name="Arabic",
            tts_language_code="ar-XA",
            tts_voice_name="ar-XA-Neural2-A",
        ),
        Language(
            abbreviation="hi",
            name="Hindi",
            tts_language_code="hi-IN",
            tts_voice_name="hi-IN-Neural2-A",
        ),
        Language(
            abbreviation="nl",
            name="Dutch",
            tts_language_code="nl-NL",
            tts_voice_name="nl-NL-Neural2-A",
        ),
        Language(
            abbreviation="pl",
            name="Polish",
            tts_language_code="pl-PL",
            tts_voice_name="pl-PL-Wavenet-A",
        ),
        Language(
            abbreviation="tr",
            name="Turkish",
            tts_language_code="tr-TR",
            tts_voice_name="tr-TR-Neural2-A",
        ),
        Language(
            abbreviation="vi",
            name="Vietnamese",
            tts_language_code="vi-VN",
            tts_voice_name="vi-VN-Neural2-A",
        ),
    ]
}
