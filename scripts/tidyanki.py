#!/usr/bin/env python3
"""Main CLI interface for tidyanki."""

import argparse
import sys
from pathlib import Path

from tidyanki.core.deduplication import (
    analyze_deck_overlap,
    deduplicate_external_deck,
    find_duplicate_cards,
    find_external_deck_duplicates,
)
from tidyanki.core.export import export_cards_to_deck, export_deduplicated_deck
from tidyanki.core.import_apkg import get_apkg_deck_names, load_cards_from_apkg
from tidyanki.core.operations import get_templates
from tidyanki.core.tables import AnkiCardsTable, AnkiDecksTable


def list_decks():
    """List all Anki decks."""
    decks = AnkiDecksTable.load()
    print(f"Found {decks.count()} decks:")
    for deck in decks.to_list():
        print(f"  {deck.name} ({deck.card_count} cards)")


def list_cards(deck_name: str, limit: int = 100):
    """List cards in a specific deck."""
    cards = AnkiCardsTable.load(deck_name=deck_name, limit=limit)
    print(f"Found {cards.count()} cards in deck '{deck_name}':")
    for card in cards.to_list():
        front = card.fields[0] if card.fields else "No content"
        print(f"  {card.id}: {front[:50]}...")


def search_cards(query: str, deck_name: str = None, limit: int = 100):
    """Search for cards by content."""
    cards = AnkiCardsTable.search(query=query, deck_name=deck_name, limit=limit)
    print(f"Found {cards.count()} cards matching '{query}':")
    for card in cards.to_list():
        front = card.fields[0] if card.fields else "No content"
        print(f"  {card.deck_name}: {front[:50]}...")


def deduplicate_deck(deck_name: str, output_path: str = None):
    """Remove duplicates from a deck and export the result."""
    print(f"Analyzing deck '{deck_name}' for duplicates...")
    
    # Find duplicates
    duplicates = find_duplicate_cards(deck_name)
    print(f"Found {duplicates.count()} duplicate cards")
    
    # Export deduplicated deck
    output_path_obj = Path(output_path) if output_path else None
    result = export_deduplicated_deck(
        new_deck_name=deck_name,
        output_path=output_path_obj
    )
    
    print(f"Exported {result.cards_created} unique cards to {result.deck_path}")


def compare_decks(deck1: str, deck2: str):
    """Analyze overlap between two decks."""
    analysis = analyze_deck_overlap(deck1, deck2)
    
    print(f"Deck comparison: '{deck1}' vs '{deck2}'")
    print(f"  {deck1}: {analysis['deck1_total_cards']} total cards")
    print(f"  {deck2}: {analysis['deck2_total_cards']} total cards")
    print(f"  Overlap: {analysis['overlap_cards']} cards")
    print(f"  {deck1} unique: {analysis['deck1_unique_cards']} cards")
    print(f"  {deck2} unique: {analysis['deck2_unique_cards']} cards")
    print(f"  Overlap percentage: {analysis['overlap_percentage_deck1']:.1f}% of {deck1}")


def list_templates():
    """List all card templates."""
    templates = get_templates()
    print(f"Found {len(templates)} templates:")
    for template in templates:
        print(f"  {template.notetype_name}: {template.name}")


def import_deduplicate(input_apkg: str, output_path: str = None, fields: str = None):
    """Import .apkg file and remove cards that already exist in collection."""
    input_path = Path(input_apkg)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Loading cards from {input_path}...")

    # Load cards from the .apkg file
    external_cards = load_cards_from_apkg(input_path)
    print(f"Found {external_cards.count()} cards in external deck")

    # Parse field indices
    comparison_fields = None
    if fields:
        try:
            comparison_fields = [int(f.strip()) for f in fields.split(",")]
            print(f"Using comparison fields: {comparison_fields}")
        except ValueError:
            raise ValueError(f"Invalid field specification: {fields}. Use comma-separated integers like '0,2'")

    # Find duplicates
    duplicates = find_external_deck_duplicates(
        input_path, comparison_fields=comparison_fields
    )
    print(f"Found {duplicates.count()} duplicate cards in collection")

    # Get unique cards
    unique_cards = deduplicate_external_deck(
        input_path, comparison_fields=comparison_fields
    )
    print(f"Found {unique_cards.count()} unique cards to export")

    if unique_cards.count() == 0:
        print("No unique cards to export!")
        return

    # Export deduplicated deck
    output_path_obj = Path(output_path) if output_path else None
    result = export_cards_to_deck(
        cards=unique_cards,
        deck_name=f"{input_path.stem} (Deduplicated)",
        output_path=output_path_obj,
    )

    print(f"Exported {result.cards_created} unique cards to {result.deck_path}")


def inspect_apkg(apkg_file: str):
    """Inspect contents of an .apkg file."""
    apkg_path = Path(apkg_file)
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    print(f"Inspecting {apkg_path}...")

    # Get deck names
    deck_names = get_apkg_deck_names(apkg_path)
    print(f"Deck names: {', '.join(deck_names)}")

    # Load and show sample cards
    cards = load_cards_from_apkg(apkg_path)
    print(f"Total cards: {cards.count()}")

    if cards.count() > 0:
        sample_cards = cards.take(5).to_list()
        print("\nSample cards:")
        for i, card in enumerate(sample_cards, 1):
            fields_preview = " | ".join(field[:30] + ("..." if len(field) > 30 else "") for field in card.fields[:3])
            print(f"  {i}. [{card.deck_name}] {fields_preview}")
        
        # Show field count distribution
        field_counts = {}
        for card in cards.to_list():
            count = len(card.fields)
            field_counts[count] = field_counts.get(count, 0) + 1
        
        print(f"\nField count distribution:")
        for count, num_cards in sorted(field_counts.items()):
            print(f"  {count} fields: {num_cards} cards")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="TidyAnki - Tools for working with Anki collections")
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
    import_parser = subparsers.add_parser("import-dedupe", help="Import .apkg and remove duplicates")
    import_parser.add_argument("input", help="Input .apkg file path")
    import_parser.add_argument("--output", help="Output .apkg file path")
    import_parser.add_argument("--fields", help="Comma-separated field indices to compare (e.g., '0,2')")
    
    # Inspect APKG
    inspect_parser = subparsers.add_parser("inspect", help="Inspect contents of .apkg file")
    inspect_parser.add_argument("apkg", help="Path to .apkg file to inspect")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "decks":
            list_decks()
        elif args.command == "cards":
            list_cards(args.deck, args.limit)
        elif args.command == "search":
            search_cards(args.query, args.deck, args.limit)
        elif args.command == "deduplicate":
            deduplicate_deck(args.deck, args.output)
        elif args.command == "compare":
            compare_decks(args.deck1, args.deck2)
        elif args.command == "templates":
            list_templates()
        elif args.command == "import-dedupe":
            import_deduplicate(args.input, args.output, args.fields)
        elif args.command == "inspect":
            inspect_apkg(args.apkg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()