"""CLI commands for tidyanki using tidyapp registry."""

import logging
from pathlib import Path

from tidyapp.registry import register

from tidyanki.audio.deck_builder import create_anki_deck, generate_audio_for_vocab
from tidyanki.config.languages import LANGUAGES
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
from tidyanki.csv.inference import infer_field_mapping, infer_missing_fields
from tidyanki.csv.parser import load_csv_items, read_csv, remove_duplicate_terms
from tidyanki.models.vocabulary import SourceMapping

logger = logging.getLogger(__name__)


@register(name="decks", description="List all Anki decks")
def list_decks() -> list[str]:
    """List all Anki decks."""
    decks = load_decks()
    result = [f"Found {decks.count()} decks:"]
    for deck in decks.to_list():
        result.append(f"  {deck.name} ({deck.card_count} cards)")
    return result


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


@register(
    name="import-dedupe",
    description="Import .apkg file and remove notes that already exist in collection",
)
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

    result = []

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


@register(
    name="create-audio-deck",
    description="Create audio flashcard deck from CSV with TTS",
)
def create_audio_deck_from_csv(
    csv_file: str,
    source_language: str,
    target_language: str,
    deck_name: str | None = None,
    output_path: str | None = None,
    deduplicate: bool = False,
    skip_inference: bool = False,
) -> str:
    """Create an Anki deck from CSV with TTS audio generation.

    Args:
        csv_file: Path to CSV file with vocabulary data
        source_language: Source language code (e.g., 'ja', 'zh', 'es')
        target_language: Target language code (e.g., 'en', 'ja')
        deck_name: Name for the Anki deck (defaults to CSV filename)
        output_path: Output path for .apkg file (defaults to <csv_name>.apkg)
        deduplicate: Deduplicate against auto-detected Anki collection
        skip_inference: Skip LLM-based field mapping and inference

    Returns:
        Status message with deck creation details
    """
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Validate languages
    if source_language not in LANGUAGES:
        available = ", ".join(LANGUAGES.keys())
        raise ValueError(f"Unknown source language: {source_language}. Available: {available}")
    if target_language not in LANGUAGES:
        available = ", ".join(LANGUAGES.keys())
        raise ValueError(f"Unknown target language: {target_language}. Available: {available}")

    source_lang = LANGUAGES[source_language]
    target_lang = LANGUAGES[target_language]

    # Set default deck name and output path
    if deck_name is None:
        deck_name = csv_path.stem
    if output_path is None:
        output_path_obj = Path(f"{csv_path.stem}_audio.apkg")
    else:
        output_path_obj = Path(output_path)

    logger.info(f"Reading CSV file: {csv_path}")
    separator, df = read_csv(csv_path)
    logger.info(f"Detected separator: '{separator}'")
    logger.info(f"Found {len(df)} rows and {len(df.columns)} columns")

    # Infer field mapping if not skipped
    if skip_inference:
        # Use simple default mapping assuming columns are in order
        field_mapping = SourceMapping(
            term=df.columns[0] if len(df.columns) > 0 else "A",
            reading=df.columns[1] if len(df.columns) > 1 else None,
            meaning=df.columns[2] if len(df.columns) > 2 else None,
            context_native=df.columns[3] if len(df.columns) > 3 else None,
            context_en=df.columns[4] if len(df.columns) > 4 else None,
        )
        logger.info(f"Using default field mapping: {field_mapping}")
    else:
        logger.info("Inferring field mapping using LLM...")
        mapping_result = infer_field_mapping(df, source_lang, target_lang)
        logger.info(f"Field mapping confidence: {mapping_result.get('confidence', 'unknown')}")
        logger.info(f"Reasoning: {mapping_result.get('reasoning', 'N/A')}")

        suggested_mapping = mapping_result.get("suggested_mapping", {})
        field_mapping = SourceMapping(
            term=suggested_mapping.get("term"),
            reading=suggested_mapping.get("reading"),
            meaning=suggested_mapping.get("meaning"),
            context_native=suggested_mapping.get("context_native"),
            context_en=suggested_mapping.get("context_en"),
        )
        logger.info(f"Using field mapping: {field_mapping}")

    # Load vocabulary items
    logger.info("Loading vocabulary items from CSV...")
    vocab_items = load_csv_items(df, field_mapping)
    logger.info(f"Loaded {len(vocab_items)} vocabulary items")

    # Infer missing fields if not skipped
    if not skip_inference:
        logger.info("Inferring missing fields using LLM...")
        vocab_items = infer_missing_fields(vocab_items, logger.info)
        logger.info(f"After inference: {len(vocab_items)} vocabulary items")

    # Remove duplicates
    vocab_items = remove_duplicate_terms(vocab_items)
    logger.info(f"After deduplication: {len(vocab_items)} unique items")

    if len(vocab_items) == 0:
        return "No vocabulary items to process!"

    # Generate audio
    logger.info("Generating TTS audio...")
    audio_mapping = generate_audio_for_vocab(
        vocab_items,
        source_language=source_lang,
        logger=logger.info,
        generate_reading_audio=True,
    )
    logger.info(f"Generated {len(audio_mapping)} audio files")

    # Create Anki deck
    logger.info(f"Creating Anki deck: {deck_name}")
    create_anki_deck(
        output_path=output_path_obj,
        vocab_items=vocab_items,
        deck_name=deck_name,
        audio_mapping=audio_mapping,
        source_language=source_lang,
        target_language=target_lang,
        logger=logger.info,
    )

    # Deduplicate against collection if enabled
    if deduplicate:
        logger.info("Deduplicating against auto-detected Anki collection...")
        collection = load_notes()
        deck_notes = load_notes_from_apkg(output_path_obj)
        unique_notes = deduplicate_external_deck(output_path_obj, collection)

        if unique_notes.count() < deck_notes.count():
            dedupe_output = Path(f"{output_path_obj.stem}_deduplicated.apkg")
            export_notes_to_deck(
                notes=unique_notes,
                deck_name=f"{deck_name} (Deduplicated)",
                output_path=dedupe_output,
            )
            logger.info(f"Deduplicated: {deck_notes.count()} -> {unique_notes.count()} notes")
            logger.info(f"Saved deduplicated deck to: {dedupe_output}")
        else:
            logger.info("No duplicates found")

    total_cards = len(vocab_items) * 2  # 2 cards per note (bidirectional)
    return f"Successfully created deck '{deck_name}' with {len(vocab_items)} notes ({total_cards} cards) at {output_path_obj}"
