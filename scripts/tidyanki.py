#!/usr/bin/env python3
"""Main CLI interface for tidyanki."""

import argparse
from pathlib import Path

from tidyanki.core.deduplication import (
    analyze_deck_overlap,
    deduplicate_external_deck,
)
from tidyanki.core.export import export_notes_to_deck
from tidyanki.core.import_apkg import (
    get_apkg_deck_names,
    load_models_from_apkg,
    load_notes_from_apkg,
)
from tidyanki.core.operations import get_templates
from tidyanki.core.tables import load_cards, load_decks, load_notes, search_cards


def list_decks():
    """List all Anki decks."""
    decks = load_decks()
    print(f"Found {decks.count()} decks:")
    for deck in decks.to_list():
        print(f"  {deck.name} ({deck.card_count} cards)")


def list_cards(deck_name: str, limit: int = 100):
    """List cards in a specific deck."""
    cards = load_cards(deck_name=deck_name).take(limit)
    print(f"Found {cards.count()} cards in deck '{deck_name}':")
    for card in cards.to_list():
        front = card.fields[0] if card.fields else "No content"
        print(f"  {card.id}: {front[:50]}...")


def search_cards_cli(query: str, deck_name: str, limit: int = 100):
    """Search for cards by content."""
    cards = search_cards(query=query, deck_name=deck_name).take(limit)
    print(f"Found {cards.count()} cards matching '{query}':")
    for card in cards.to_list():
        front = card.fields[0] if card.fields else "No content"
        print(f"  {card.deck_name}: {front[:50]}...")


def compare_decks(deck1: str, deck2: str):
    """Analyze overlap between two decks."""
    analysis = analyze_deck_overlap(deck1, deck2)

    print(f"Deck comparison: '{deck1}' vs '{deck2}'")
    print(f"  {deck1}: {analysis['deck1_total_notes']} total notes")
    print(f"  {deck2}: {analysis['deck2_total_notes']} total notes")
    print(f"  Overlap: {analysis['overlap_notes']} notes")
    print(f"  {deck1} unique: {analysis['deck1_unique_notes']} notes")
    print(f"  {deck2} unique: {analysis['deck2_unique_notes']} notes")
    print(f"  Overlap percentage: {analysis['overlap_percentage_deck1']:.1f}% of {deck1}")


def list_templates():
    """List all card templates."""
    templates = get_templates()
    print(f"Found {len(templates)} templates:")
    for template in templates:
        print(f"  {template.notetype_name}: {template.name}")


def import_deduplicate(input_apkg: str, output_path: Path):
    """Import .apkg file and remove notes that already exist in collection."""
    input_path = Path(input_apkg)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Loading notes from {input_path}...")
    collection = load_notes()
    print(f"Comparing against {collection.count()} notes in your collection...")

    unique_notes = deduplicate_external_deck(input_path, collection)
    print(f"Found {unique_notes.count()} unique notes to export")

    if unique_notes.count() == 0:
        print("No unique notes to export!")
        return

    result = export_notes_to_deck(
        notes=unique_notes,
        deck_name=f"{input_path.stem} (Deduplicated)",
        output_path=Path(output_path),
    )

    print(
        f"Exported {result.cards_created} cards from {unique_notes.count()} unique notes to {result.deck_path}"
    )


def inspect_apkg(apkg_file: str):
    """Inspect contents of an .apkg file."""
    apkg_path = Path(apkg_file)
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    print(f"Inspecting {apkg_path}...")

    # Get deck names
    deck_names = get_apkg_deck_names(apkg_path)
    print(f"Deck names: {', '.join(deck_names)}")

    # Load and show sample notes
    notes = load_notes_from_apkg(apkg_path)
    models = load_models_from_apkg(apkg_path)
    print(f"Total notes: {notes.count()}")
    print(f"Total models: {len(models)}")

    # Estimate total cards from notes and their models
    total_cards = sum(len(note.model.templates) for note in notes.to_list() if note.model)
    print(f"Estimated total cards: {total_cards}")

    if notes.count() > 0:
        sample_notes = notes.take(5).to_list()
        print("\nSample notes:")
        for i, note in enumerate(sample_notes, 1):
            fields_preview = " | ".join(
                field[:30] + ("..." if len(field) > 30 else "") for field in note.fields[:3]
            )
            print(f"  {i}. [Note {note.id}] {fields_preview}")

        # Show field count distribution
        field_counts: dict[int, int] = {}
        for note in notes.to_list():
            count = len(note.fields)
            field_counts[count] = field_counts.get(count, 0) + 1  # type: ignore

        print("\nField count distribution:")
        for count, num_notes in sorted(field_counts.items()):
            print(f"  {count} fields: {num_notes} notes")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TidyAnki - Tools for working with Anki collections"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List decks
    subparsers.add_parser("decks", help="List all decks")

    # List cards
    cards_parser = subparsers.add_parser("cards", help="List cards in a deck")
    cards_parser.add_argument("deck", help="Deck name")
    cards_parser.add_argument("--limit", type=int, default=100, help="Maximum number of cards")

    # Search cards
    search_parser = subparsers.add_parser("search", help="Search for cards")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--deck", help="Limit search to specific deck")
    search_parser.add_argument("--limit", type=int, default=100, help="Maximum number of results")

    # Deduplicate deck
    dedup_parser = subparsers.add_parser("deduplicate", help="Remove duplicates from a deck")
    dedup_parser.add_argument("deck", help="Deck name to deduplicate")
    dedup_parser.add_argument("--output", help="Output file path")

    # Compare decks
    compare_parser = subparsers.add_parser("compare", help="Compare two decks for overlap")
    compare_parser.add_argument("deck1", help="First deck name")
    compare_parser.add_argument("deck2", help="Second deck name")

    # List templates
    subparsers.add_parser("templates", help="List all card templates")

    # Import and deduplicate
    import_parser = subparsers.add_parser(
        "import-dedupe", help="Import .apkg and remove duplicates"
    )
    import_parser.add_argument("input", help="Input .apkg file path")
    import_parser.add_argument("--output", help="Output .apkg file path")

    # Inspect APKG
    inspect_parser = subparsers.add_parser("inspect", help="Inspect contents of .apkg file")
    inspect_parser.add_argument("apkg", help="Path to .apkg file to inspect")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "decks":
        list_decks()
    elif args.command == "cards":
        list_cards(args.deck, args.limit)
    elif args.command == "search":
        search_cards_cli(args.query, args.deck, args.limit)
    elif args.command == "compare":
        compare_decks(args.deck1, args.deck2)
    elif args.command == "templates":
        list_templates()
    elif args.command == "import-dedupe":
        import_deduplicate(args.input, args.output)
    elif args.command == "inspect":
        inspect_apkg(args.apkg)


if __name__ == "__main__":
    main()