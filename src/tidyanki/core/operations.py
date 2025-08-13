"""Core operations for working with Anki data."""

import hashlib
import shutil
import tempfile
from pathlib import Path

import genanki

from tidyanki.models.anki_models import (
    AddVocabCardRequest,
    AnkiCreateResult,
    AnkiTemplate,
    AnkiTemplateContent,
    ExampleSentenceResponse,
)

from .anki_db import get_anki_db_path, setup_anki_connection


def get_templates() -> list[AnkiTemplate]:
    """Get all card templates with their note types."""
    anki_db = get_anki_db_path()
    if not anki_db:
        return []

    with setup_anki_connection(anki_db) as conn:
        cursor = conn.execute(
            """
            SELECT t.name as template_name, 
                   nt.name as notetype_name, 
                   t.ntid as notetype_id
            FROM templates t 
            JOIN notetypes nt ON t.ntid = nt.id 
            ORDER BY nt.name, t.ord
            """
        )
        rows = cursor.fetchall()

        templates = []
        for row in rows:
            templates.append(
                AnkiTemplate(
                    name=row["template_name"],
                    notetype_name=row["notetype_name"],
                    notetype_id=row["notetype_id"],
                )
            )

    return templates


def _decode_template_config(config_blob: bytes) -> tuple[str, str, str]:
    """Decode template config from binary protobuf format.

    Returns tuple of (front_html, back_html, browser_question)
    """
    try:
        # The config is stored as protobuf with field tags
        # Field 1: question/front HTML
        # Field 2: answer/back HTML
        # Field 3: browser question HTML

        # Simple protobuf parsing for these string fields
        config_str = config_blob.decode("utf-8", errors="ignore")

        # Extract strings between protobuf delimiters
        parts = []
        i = 0
        while i < len(config_str):
            if ord(config_str[i]) == 0x0A:  # String field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i : i + length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            elif ord(config_str[i]) == 0x12:  # Another string field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i : i + length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            elif ord(config_str[i]) == 0x1A:  # Third string field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i : i + length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            else:
                i += 1

        # Ensure we have at least 3 parts
        while len(parts) < 3:
            parts.append("")

        return parts[0], parts[1], parts[2]

    except Exception:
        return "", "", ""


def get_template_content(template_name: str, notetype_name: str) -> AnkiTemplateContent | None:
    """Get HTML content for a specific template.

    Args:
        template_name: Name of the template
        notetype_name: Name of the note type
    """
    anki_db = get_anki_db_path()
    if not anki_db:
        return None

    with setup_anki_connection(anki_db) as conn:
        cursor = conn.execute(
            """
            SELECT t.name as template_name, 
                   nt.name as notetype_name, 
                   t.config
            FROM templates t 
            JOIN notetypes nt ON t.ntid = nt.id 
            WHERE t.name = ? AND nt.name = ?
            """,
            (template_name, notetype_name),
        )
        row = cursor.fetchone()

        if not row:
            return None

        front_html, back_html, browser_question = _decode_template_config(row["config"])

        return AnkiTemplateContent(
            name=row["template_name"],
            notetype_name=row["notetype_name"],
            front_html=front_html,
            back_html=back_html,
            browser_question=browser_question,
        )


def create_vocab_cards(
    deck_name: str,
    cards: list[AddVocabCardRequest],
) -> AnkiCreateResult:
    """Create multiple bilingual vocabulary cards with audio and add to Anki deck.

    Args:
        deck_name: Name of the Anki deck
        cards: List of vocabulary cards to add
    """
    # Generate deck ID from name
    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    # Create temporary directory for media files
    temp_dir = tempfile.TemporaryDirectory()
    media_files = []

    def _add_audio(audio_path: Path | None, term: str) -> str:
        """Add audio file to package with content-based filename."""
        if not audio_path or not audio_path.exists():
            return ""

        # Create a unique filename based on content hash
        audio_filename = f"audio_{hashlib.md5(term.encode()).hexdigest()[:8]}.mp3"
        temp_audio_path = Path(temp_dir.name) / audio_filename
        shutil.copy2(audio_path, temp_audio_path)
        media_files.append(temp_audio_path)

        return f"[sound:{audio_filename}]"

    # Process each card
    for card in cards:
        # Handle audio files
        term_audio_field = _add_audio(card.audio_ja, card.term_ja)
        meaning_audio_field = _add_audio(card.audio_en, card.term_en)

        # Note: This function needs to be updated to use user-selected templates
        # For now, this is a placeholder that would need template selection
        note = genanki.Note(
            model=None,  # Would be user-selected template
            fields=[
                card.term_ja,  # Term
                card.reading_ja,  # Reading
                card.term_en,  # Meaning
                card.sentence_ja,  # Example
                card.sentence_en,  # ExampleTranslation
                term_audio_field,  # TermAudio
                meaning_audio_field,  # MeaningAudio
            ],
        )
        deck.add_note(note)

    # Determine output path in temp directory
    output_temp_dir = Path(tempfile.gettempdir())
    output_path = output_temp_dir / f"{deck_name.replace(' ', '_')}_vocab.apkg"

    # Create package with media files
    package = genanki.Package(deck)
    if media_files:
        package.media_files = media_files

    try:
        package.write_to_file(str(output_path))
        result = AnkiCreateResult(
            deck_path=output_path,
            cards_created=len(cards),
            message=f"Created {len(cards)} bilingual vocab cards in deck '{deck_name}'",
        )
    except Exception as e:
        result = AnkiCreateResult(
            deck_path=output_path,
            cards_created=0,
            message=f"Failed to create deck '{deck_name}': {str(e)}",
        )
    finally:
        # Clean up temporary directory
        temp_dir.cleanup()

    return result


def generate_example_sentence(
    word: str,
    translation: str,
    source_language: str = "en",
    target_language: str = "ja",
    difficulty: str = "intermediate",
) -> ExampleSentenceResponse:
    """Generate example sentences for a vocabulary word using LLM.

    Args:
        word: The vocabulary word
        translation: Translation of the word
        source_language: Source language code
        target_language: Target language code
        difficulty: Difficulty level (beginner, intermediate, advanced)

    Returns:
        Example sentences for source and target languages
    """
    # TODO: This would require tidyschema.adapters.llm which is not available
    # For now, return a placeholder
    return ExampleSentenceResponse(
        source_sentence=f"Example sentence with {word}.",
        target_sentence=f"Example sentence with {translation}.",
    )
