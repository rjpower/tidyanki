"""CLI commands for tidyanki using tidyapp registry."""

import logging
from pathlib import Path

from tidyapp.registry import register

from tidyanki.core.deduplication import (
    analyze_deck_overlap,
    deduplicate_external_deck,
)
from tidyanki.core.export_apkg import export_notes_to_deck
from tidyanki.core.extract_fields import extract_fields_from_notes
from tidyanki.core.import_apkg import (
    get_apkg_deck_names,
    load_models_from_apkg,
    load_notes_from_apkg,
)
from tidyanki.core.operations import get_templates
from tidyanki.core.tables import load_cards, load_decks, load_notes, search_cards

logger = logging.getLogger(__name__)


@register(name="decks", description="List all Anki decks")
def list_decks() -> str:
    """List all Anki decks."""
    decks = load_decks()
    result = [f"Found {decks.count()} decks:"]
    for deck in decks.to_list():
        result.append(f"  {deck.name} ({deck.card_count} cards)")
    return "\n".join(result)


@register(name="cards", description="List cards in a specific deck")
def list_cards(deck_name: str, limit: int = 100) -> str:
    """List cards in a specific deck."""
    cards = load_cards(deck_name=deck_name).take(limit)
    result = [f"Found {cards.count()} cards in deck '{deck_name}':"]
    
    for card in cards.to_list():
        result.append("")
        result.append("Detailed card:")
        result.append(f"  Card ID: {card.id}")
        result.append(f"  Note ID: {card.note_id}")
        result.append(f"  Card Type: {card.card_type}")
        result.append(f"  Deck: {card.deck_name}")
        result.append(f"  Tags: {', '.join(card.tags) if card.tags else 'None'}")
        result.append(f"  Fields ({len(card.fields)}):")
        for i, field in enumerate(card.fields):
            result.append(f"    [{i}]: {field}")
    
    return "\n".join(result)


@register(name="search", description="Search for cards by content")
def search_cards_cli(query: str, deck_name: str | None = None, limit: int = 100) -> str:
    """Search for cards by content."""
    cards = search_cards(query=query, deck_name=deck_name).take(limit)
    result = [f"Found {cards.count()} cards matching '{query}':"]
    
    for card in cards.to_list():
        result.append("")
        result.append("Detailed card:")
        result.append(f"  Card ID: {card.id}")
        result.append(f"  Note ID: {card.note_id}")
        result.append(f"  Card Type: {card.card_type}")
        result.append(f"  Deck: {card.deck_name}")
        result.append(f"  Tags: {', '.join(card.tags) if card.tags else 'None'}")
        result.append(f"  Fields ({len(card.fields)}):")
        for i, field in enumerate(card.fields):
            result.append(f"    [{i}]: {field}")
    
    return "\n".join(result)


@register(name="compare", description="Analyze overlap between two decks")
def compare_decks(deck1: str, deck2: str) -> str:
    """Analyze overlap between two decks."""
    analysis = analyze_deck_overlap(deck1, deck2)
    
    result = [
        f"Deck comparison: '{deck1}' vs '{deck2}'",
        f"  {deck1}: {analysis['deck1_total_notes']} total notes",
        f"  {deck2}: {analysis['deck2_total_notes']} total notes",
        f"  Overlap: {analysis['overlap_notes']} notes",
        f"  {deck1} unique: {analysis['deck1_unique_notes']} notes",
        f"  {deck2} unique: {analysis['deck2_unique_notes']} notes",
        f"  Overlap percentage: {analysis['overlap_percentage_deck1']:.1f}% of {deck1}",
    ]
    return "\n".join(result)


@register(name="templates", description="List all card templates")
def list_templates() -> str:
    """List all card templates."""
    templates = get_templates()
    result = [f"Found {len(templates)} templates:"]
    for template in templates:
        result.append(f"  {template.notetype_name}: {template.name}")
    return "\n".join(result)


@register(name="import-dedupe", description="Import .apkg file and remove notes that already exist in collection")
def import_deduplicate(input_apkg: str, output_path: str | None = None) -> str:
    """Import .apkg file and remove notes that already exist in collection."""
    input_path = Path(input_apkg)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info(f"Loading notes from {input_path}...")
    collection = load_notes()
    logger.info(f"Comparing against {collection.count()} notes in your collection...")

    unique_notes = deduplicate_external_deck(input_path, collection)
    logger.info(f"Found {unique_notes.count()} unique notes to export")

    if len(unique_notes) == 0:
        return "No unique notes to export!"

    if output_path is None:
        output_path_obj = Path(f"{input_path.stem}_deduplicated.apkg")
    else:
        output_path_obj = Path(output_path)

    result = export_notes_to_deck(
        notes=unique_notes,
        deck_name=f"{input_path.stem} (Deduplicated)",
        output_path=output_path_obj,
    )

    return f"Exported {result.cards_created} cards from {unique_notes.count()} unique notes to {result.deck_path}"


@register(name="extract-fields", description="Extract fields from .apkg file as CSV")
def extract_fields_from_apkg(apkg_file: str, field_indices: str = "0") -> str:
    """Extract fields from .apkg file as CSV."""
    apkg_path = Path(apkg_file)
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    notes = load_notes_from_apkg(apkg_path)
    logger.info(f"Loaded {notes.count()} notes from {apkg_path}")

    indices = [int(x.strip()) for x in field_indices.split(",")]
    csv_output = extract_fields_from_notes(notes, field_indices=indices)
    return csv_output


@register(name="inspect", description="Inspect contents of .apkg file")
def inspect_apkg(apkg_file: str) -> str:
    """Inspect contents of an .apkg file."""
    apkg_path = Path(apkg_file)
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    result = [f"Inspecting {apkg_path}..."]

    # Get deck names
    deck_names = get_apkg_deck_names(apkg_path)
    result.append(f"Deck names: {', '.join(deck_names)}")

    # Load and show sample notes
    notes = load_notes_from_apkg(apkg_path)
    models = load_models_from_apkg(apkg_path)
    result.append(f"Total notes: {notes.count()}")
    result.append(f"Total models: {len(models)}")

    # Estimate total cards from notes and their models
    total_cards = sum(len(note.model.templates) for note in notes.to_list() if note.model)
    result.append(f"Estimated total cards: {total_cards}")

    if notes.count() > 0:
        first_note = notes.take(1).to_list()[0]
        result.append("")
        result.append("Detailed first note:")
        result.append(f"  Note ID: {first_note.id}")
        result.append(f"  GUID: {first_note.guid}")
        result.append(f"  Model ID: {first_note.mid}")
        result.append(f"  Tags: {', '.join(first_note.tags) if first_note.tags else 'None'}")
        result.append(f"  Fields ({len(first_note.fields)}):")
        for i, field in enumerate(first_note.fields):
            result.append(f"    [{i}]: {field}")

        sample_notes = notes.take(5).to_list()
        result.append("")
        result.append("Sample notes:")
        for i, note in enumerate(sample_notes, 1):
            fields_preview = " | ".join(
                field[:30] + ("..." if len(field) > 30 else "") for field in note.fields[:3]
            )
            result.append(f"  {i}. [Note {note.id}] {fields_preview}")

        # Show field count distribution
        field_counts: dict[int, int] = {}
        for note in notes.to_list():
            count = len(note.fields)
            field_counts[count] = field_counts.get(count, 0) + 1

        result.append("")
        result.append("Field count distribution:")
        for count, num_notes in sorted(field_counts.items()):
            result.append(f"  {count} fields: {num_notes} notes")

    return "\n".join(result)