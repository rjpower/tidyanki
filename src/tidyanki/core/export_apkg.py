"""Deck export functionality using genanki."""

import tempfile
from pathlib import Path

import genanki
from tidylinq import Enumerable

from tidyanki.models.anki_models import AnkiCreateResult, AnkiNote


def export_notes_to_deck(
    notes: Enumerable[AnkiNote],
    deck_name: str,
    output_path: Path | None = None,
) -> AnkiCreateResult:
    """Export a table of notes to an Anki deck file.

    Args:
        notes: Table of notes to export (each note should have model reference)
        deck_name: Name for the exported deck
        output_path: Optional output path. If None, uses temp directory.

    Returns:
        Result with path to created deck file
    """
    # Generate deck ID from name
    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    note_list = notes.to_list()
    all_media_files = []

    # Convert notes to genanki notes
    for anki_note in note_list:
        if anki_note.model is None:
            raise ValueError(f"Note {anki_note.id} has no model reference")

        genanki_model = anki_note.model.to_genanki_model()

        expected_field_count = len(anki_note.model.fields)
        assert len(anki_note.fields) == expected_field_count, (
            f"Field count mismatch: {anki_note.fields} vs {expected_field_count}"
        )

        note = genanki.Note(model=genanki_model, fields=anki_note.fields, tags=anki_note.tags)
        deck.add_note(note)
        
        # Collect media files from this note
        all_media_files.extend(anki_note.media_files)

    # Determine output path
    if output_path is None:
        output_temp_dir = Path(tempfile.gettempdir())
        output_path = output_temp_dir / f"{deck_name.replace(' ', '_')}.apkg"

    # Create package with media files
    package = genanki.Package(deck)
    if all_media_files:
        # Create temporary files for media data and collect their paths
        temp_media_dir = Path(tempfile.mkdtemp())
        media_file_paths = []
        
        # Remove duplicate MediaFile objects while preserving order
        seen_filenames = set()
        unique_media_files = []
        for media_file in all_media_files:
            if media_file.filename not in seen_filenames:
                unique_media_files.append(media_file)
                seen_filenames.add(media_file.filename)
        
        # Write MediaFile data to temporary files
        for media_file in unique_media_files:
            temp_file_path = temp_media_dir / media_file.filename
            temp_file_path.write_bytes(media_file.data)
            media_file_paths.append(str(temp_file_path))
        
        package.media_files = media_file_paths

    package.write_to_file(str(output_path))

    # Count total cards that will be generated (depends on note type templates)
    total_cards = sum(len(note.model.templates) for note in note_list if note.model)

    return AnkiCreateResult(
        deck_path=output_path,
        cards_created=total_cards,
        message=f"Exported {len(note_list)} notes ({total_cards} cards) to deck '{deck_name}'",
    )
