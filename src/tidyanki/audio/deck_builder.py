import hashlib
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import genanki

from tidyanki.config.languages import Language
from tidyanki.models.vocabulary import VocabItem
from tidyanki.tts.audio_generation import TTSAudio, generate_tts_audio

ANKI_MODEL_ID = 1607392319


def _id_from_name(name: str) -> int:
    """Generate Anki deck ID from name"""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


ANKI_CARD_CSS = """
.card {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic Pro", "Yu Gothic", Meiryo, sans-serif;
    font-size: 24px;
    text-align: center;
    color: #2c3e50;
    background-color: #f8f9fa;
    max-width: 800px;
    margin: 20px auto;
    padding: 20px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    border-radius: 8px;
}
.term {
    font-size: 32px;
    color: #2c3e50;
    margin-bottom: 15px;
    font-weight: bold;
}
.reading {
    font-size: 20px;
    color: #666;
    margin: 15px 0;
    font-family: "Hiragino Sans", sans-serif;
}
.meaning {
    font-size: 22px;
    color: #34495e;
    margin: 15px 0;
    padding: 10px;
    background-color: #e9ecef;
    border-radius: 5px;
}
ruby {
    font-size: 20px;
}
rt {
    font-size: 12px;
    color: #666;
}
hr#answer {
    border: none;
    border-top: 2px solid #dee2e6;
    margin: 20px 0;
}
.example {
    font-size: 18px;
    color: #495057;
    margin: 15px 0;
    line-height: 1.6;
    padding: 15px;
    background-color: #fff;
    border-left: 4px solid #4CAF50;
    border-radius: 4px;
}
.example-translation {
    font-size: 16px;
    color: #666;
    font-style: italic;
    margin: 10px 0;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 4px;
}
"""


@dataclass
class AudioData:
    term: str
    data: bytes


def generate_audio_for_vocab(
    items: Sequence[VocabItem],
    source_language: Language,
    logger: Callable[[str], None],
    max_workers: int = 16,
    generate_reading_audio: bool = True,
) -> dict[str, AudioData]:
    """Generate audio for vocabulary items using parallel processing

    Generates audio for:
    - term field (using reading if available, otherwise term)
    - reading field (if generate_reading_audio is True and reading exists)

    Args:
        items: Vocabulary items to generate audio for
        source_language: Language configuration for TTS
        logger: Progress logging function
        max_workers: Maximum parallel workers for audio generation
        generate_reading_audio: Whether to generate separate audio for reading field

    Returns:
        Dictionary mapping text to AudioData
    """
    audio_mapping = {}

    # Create a list of all terms we need to generate audio for
    items_to_process = []
    for item in items:
        # Generate audio for the term (using reading if available)
        text_for_audio = item.reading if item.reading else item.term
        if text_for_audio:
            items_to_process.append(text_for_audio)

        # Optionally generate separate audio for reading
        if generate_reading_audio and item.reading:
            items_to_process.append(item.reading)

    # Deduplicate
    items_to_process = list(set(items_to_process))
    total = len(items_to_process)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for text in items_to_process:
            future = executor.submit(generate_tts_audio, text, source_language)
            futures[text] = future

        # Process results as they complete
        for text, future in futures.items():
            try:
                tts_audio: TTSAudio | None = future.result()
                completed += 1
                if tts_audio and tts_audio.data:
                    logger(
                        f"Generated audio for '{tts_audio.text}' -- {completed}/{total} ({completed / total * 100:.1f}%)"
                    )
                    audio_mapping[text] = AudioData(tts_audio.text, tts_audio.data)
                else:
                    logger(f"Skipped audio for '{text}' (no TTS data)")
            except Exception as e:
                logger(f"Error generating audio for '{text}': {e}")

    logger(f"Completed audio generation for {len(audio_mapping)} terms")
    return audio_mapping


def create_anki_deck(
    output_path: Path,
    vocab_items: list[VocabItem],
    deck_name: str,
    audio_mapping: dict[str, AudioData],
    source_language: Language,
    target_language: Language,
    logger: Callable[[str], None] = print,
) -> genanki.Package:
    """Create an Anki deck package (.apkg) from vocabulary items

    Args:
        output_path: Path to write the .apkg file
        vocab_items: List of vocabulary items to include
        deck_name: Name for the Anki deck
        audio_mapping: Dictionary mapping text to audio data
        source_language: Source language configuration
        target_language: Target language configuration
        logger: Progress logging function

    Returns:
        genanki.Package object
    """
    # Initialize model with fixed ID
    model = genanki.Model(
        ANKI_MODEL_ID,
        f"{source_language.name} Vocabulary",
        fields=[
            {"name": "Term"},
            {"name": "Reading"},
            {"name": "Meaning"},
            {"name": "Example"},
            {"name": "ExampleTranslation"},
            {"name": "TermAudio"},
            {"name": "ReadingAudio"},
        ],
        templates=[
            {
                "name": f"{source_language.name} to {target_language.name}",
                "qfmt": """
                    <div class="term">{{Term}}</div>
                    {{TermAudio}}
                    <div class="example">{{Example}}</div>
                """,
                "afmt": """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="reading">{{Reading}}</div>
                    {{ReadingAudio}}
                    <div class="meaning">{{Meaning}}</div>
                    <div class="example-translation">{{ExampleTranslation}}</div>
                """,
            },
            {
                "name": f"{target_language.name} to {source_language.name}",
                "qfmt": """
                    <div class="meaning">{{Meaning}}</div>
                    <div class="example-translation">{{ExampleTranslation}}</div>
                """,
                "afmt": """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="term">{{Term}}</div>
                    {{TermAudio}}
                    <div class="reading">{{Reading}}</div>
                    {{ReadingAudio}}
                    <div class="example">{{Example}}</div>
                """,
            },
        ],
        css=ANKI_CARD_CSS,
    )

    deck = genanki.Deck(deck_id=_id_from_name(deck_name), name=deck_name)

    media_files = []

    # Create temporary directory for media files
    temp_dir = tempfile.TemporaryDirectory()

    def _add_audio(text: str) -> str:
        """Add audio file and return Anki audio tag"""
        if not text or text not in audio_mapping:
            return ""
        audio_filename = f"audio_{hashlib.md5(text.encode()).hexdigest()[:8]}.mp3"
        audio_path = Path(temp_dir.name) / audio_filename
        audio_path.write_bytes(audio_mapping[text].data)
        media_files.append(str(audio_path))
        return f"[sound:{audio_filename}]"

    for item in vocab_items:
        # Prepare fields
        term_audio_text = item.reading if item.reading else item.term
        fields = [
            item.term,
            item.reading,
            item.meaning,
            item.context_native or "",
            item.context_en or "",
            _add_audio(term_audio_text),  # Term audio
            _add_audio(item.reading),  # Reading audio
        ]

        note = genanki.Note(model=model, fields=fields)
        deck.add_note(note)

    logger(f"Created deck with {len(vocab_items)} cards")

    package = genanki.Package([deck])
    package.media_files = media_files
    package.write_to_file(output_path)

    return package
