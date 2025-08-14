"""Deck export functionality using genanki."""

import tempfile
from pathlib import Path

import genanki
from tidylinq import Enumerable

from tidyanki.models.anki_models import AnkiCard, AnkiCreateResult


def export_cards_to_deck(
    cards: Enumerable[AnkiCard],
    deck_name: str,
    output_path: Path | None = None,
    media_files: list[str] | None = None,
) -> AnkiCreateResult:
    """Export a table of cards to an Anki deck file using original models.

    Args:
        cards: Table of cards to export (each card should have model reference)
        deck_name: Name for the exported deck
        output_path: Optional output path. If None, uses temp directory.
        media_files: Optional list of media file paths to include

    Returns:
        Result with path to created deck file
    """
    # Generate deck ID from name
    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    # Group cards by their source note to recreate the original note structure
    card_list = cards.to_list()
    notes_by_id = {}

    for card in card_list:
        if card.model is None:
            raise ValueError(f"Card {card.id} has no model reference")
        if card.note_id is None:
            raise ValueError(f"Card {card.id} has no note_id reference")

        note_id = card.note_id
        if note_id not in notes_by_id:
            # Use the first card to represent the note's data
            notes_by_id[note_id] = {
                "fields": card.fields[:],
                "tags": card.tags[:],
                "model": card.model,
                "cards": [],
            }
        notes_by_id[note_id]["cards"].append(card)

    # Convert grouped note data to genanki notes
    for _, note_data in notes_by_id.items():
        anki_model = note_data["model"]
        genanki_model = anki_model.to_genanki_model()

        # Use original field structure
        fields = note_data["fields"][:]

        # Ensure we have the right number of fields for this model
        expected_field_count = len(anki_model.fields)
        while len(fields) < expected_field_count:
            fields.append("")

        # Truncate if we have too many fields (shouldn't happen with original models)
        fields = fields[:expected_field_count]

        # Create one genanki note (which will generate multiple cards based on templates)
        note = genanki.Note(model=genanki_model, fields=fields, tags=note_data["tags"])
        deck.add_note(note)

    # Determine output path
    if output_path is None:
        output_temp_dir = Path(tempfile.gettempdir())
        output_path = output_temp_dir / f"{deck_name.replace(' ', '_')}.apkg"

    # Create package with media files
    package = genanki.Package(deck)
    if media_files:
        package.media_files = media_files

    package.write_to_file(str(output_path))

    return AnkiCreateResult(
        deck_path=output_path,
        cards_created=len(card_list),
        message=f"Exported {len(notes_by_id)} notes ({len(card_list)} cards) to deck '{deck_name}'",
    )
