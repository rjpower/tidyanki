"""Deck export functionality using genanki."""

import tempfile
from pathlib import Path

import genanki
from tidylinq import Table

from tidyanki.models.anki_models import AnkiCard, AnkiCreateResult

# Basic model for exported cards
BASIC_MODEL = genanki.Model(
    1607392319,
    "TidyAnki Basic Model",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
        },
    ],
)

# Vocabulary model for language learning
VOCAB_MODEL = genanki.Model(
    1607392320,
    "TidyAnki Vocabulary Model",
    fields=[
        {"name": "Term"},
        {"name": "Reading"},
        {"name": "Meaning"},
        {"name": "Example"},
        {"name": "ExampleTranslation"},
        {"name": "TermAudio"},
        {"name": "MeaningAudio"},
    ],
    templates=[
        {
            "name": "Term to Meaning",
            "qfmt": "{{Term}}<br>{{Reading}}<br>{{TermAudio}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Meaning}}<br>{{Example}}<br>{{ExampleTranslation}}<br>{{MeaningAudio}}',
        },
        {
            "name": "Meaning to Term",
            "qfmt": "{{Meaning}}<br>{{MeaningAudio}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Term}}<br>{{Reading}}<br>{{Example}}<br>{{ExampleTranslation}}<br>{{TermAudio}}',
        },
    ],
)


def export_cards_to_deck(
    cards: Table[AnkiCard],
    deck_name: str,
    output_path: Path | None = None,
    model: genanki.Model | None = None,
) -> AnkiCreateResult:
    """Export a table of cards to an Anki deck file.

    Args:
        cards: Table of cards to export
        deck_name: Name for the exported deck
        output_path: Optional output path. If None, uses temp directory.
        model: Optional Anki model to use. If None, uses basic model.

    Returns:
        Result with path to created deck file
    """
    if model is None:
        model = BASIC_MODEL

    # Generate deck ID from name
    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    # Convert cards to genanki notes
    card_list = cards.to_list()
    for card in card_list:
        # Ensure we have enough fields for the model
        fields = card.fields[:]
        while len(fields) < len(model.fields):
            fields.append("")

        # Truncate if we have too many fields
        fields = fields[: len(model.fields)]

        note = genanki.Note(model=model, fields=fields, tags=card.tags)
        deck.add_note(note)

    # Determine output path
    if output_path is None:
        output_temp_dir = Path(tempfile.gettempdir())
        output_path = output_temp_dir / f"{deck_name.replace(' ', '_')}.apkg"

    # Create and write package
    package = genanki.Package(deck)
    package.write_to_file(str(output_path))

    return AnkiCreateResult(
        deck_path=output_path,
        cards_created=len(card_list),
        message=f"Exported {len(card_list)} cards to deck '{deck_name}'",
    )


def export_deduplicated_deck(
    new_deck_name: str,
    output_deck_name: str | None = None,
    output_path: Path | None = None,
    comparison_field_index: int = 0,
) -> AnkiCreateResult:
    """Export a deck with duplicates removed.

    Args:
        new_deck_name: Name of the deck to deduplicate and export
        output_deck_name: Name for the output deck. If None, uses "{new_deck_name} (Deduplicated)"
        output_path: Optional output path. If None, uses temp directory.
        comparison_field_index: Which field index to use for duplicate comparison

    Returns:
        Result with path to created deck file
    """
    from .deduplication import remove_duplicate_cards

    if output_deck_name is None:
        output_deck_name = f"{new_deck_name} (Deduplicated)"

    # Get unique cards
    unique_cards = remove_duplicate_cards(
        new_deck_name=new_deck_name, comparison_field_index=comparison_field_index
    )

    # Choose appropriate model based on field count
    if unique_cards.any(lambda card: len(card.fields) >= 7):
        model = VOCAB_MODEL
    else:
        model = BASIC_MODEL

    return export_cards_to_deck(
        cards=unique_cards, deck_name=output_deck_name, output_path=output_path, model=model
    )


def export_filtered_deck(
    cards: Table[AnkiCard], deck_name: str, output_path: Path | None = None
) -> AnkiCreateResult:
    """Export a filtered set of cards to a new deck.

    Args:
        cards: Pre-filtered table of cards to export
        deck_name: Name for the exported deck
        output_path: Optional output path. If None, uses temp directory.

    Returns:
        Result with path to created deck file
    """
    # Choose appropriate model based on field count
    if cards.any(lambda card: len(card.fields) >= 7):
        model = VOCAB_MODEL
    else:
        model = BASIC_MODEL

    return export_cards_to_deck(
        cards=cards, deck_name=deck_name, output_path=output_path, model=model
    )
