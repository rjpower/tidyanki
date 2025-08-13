#!/usr/bin/env python3
"""Main CLI interface for tidyanki."""

import argparse
import sys
from pathlib import Path

from tidyanki.core.deduplication import analyze_deck_overlap, find_duplicate_cards
from tidyanki.core.export import export_deduplicated_deck
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
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()