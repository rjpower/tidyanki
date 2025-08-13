"""Deck deduplication functionality."""

from collections.abc import Callable

from tidylinq import Table

from tidyanki.models.anki_models import AnkiCard

from .tables import AnkiCardsTable


def find_duplicate_cards(
    new_deck_name: str,
    existing_collection: Table[AnkiCard] | None = None,
    comparison_field_index: int = 0,
    custom_comparison: Callable[[str, str], bool] | None = None,
) -> Table[AnkiCard]:
    """Find cards in new deck that already exist in the collection.

    Args:
        new_deck_name: Name of the new deck to check for duplicates
        existing_collection: Optional pre-loaded collection cards. If None, loads all cards.
        comparison_field_index: Which field index to compare (default: 0 for first field)
        custom_comparison: Optional custom comparison function

    Returns:
        Table of duplicate cards
    """
    # Load new deck cards
    new_cards = AnkiCardsTable.load(deck_name=new_deck_name)

    # Load existing collection if not provided
    if existing_collection is None:
        existing_collection = AnkiCardsTable.load()

    # Filter out cards from the new deck itself from existing collection
    existing_cards = existing_collection.where(lambda card: card.deck_name != new_deck_name)

    # Define comparison function
    if custom_comparison is None:

        def default_comparison(new_field: str, existing_field: str) -> bool:
            return new_field.strip().lower() == existing_field.strip().lower()

        comparison_func = default_comparison
    else:
        comparison_func = custom_comparison

    # Find duplicates
    duplicates = new_cards.where(
        lambda new_card: existing_cards.any(
            lambda existing_card: (
                len(new_card.fields) > comparison_field_index
                and len(existing_card.fields) > comparison_field_index
                and comparison_func(
                    new_card.fields[comparison_field_index],
                    existing_card.fields[comparison_field_index],
                )
            )
        )
    )

    return Table.from_rows(list(duplicates), AnkiCard)


def remove_duplicate_cards(
    new_deck_name: str,
    existing_collection: Table[AnkiCard] | None = None,
    comparison_field_index: int = 0,
    custom_comparison: Callable[[str, str], bool] | None = None,
) -> Table[AnkiCard]:
    """Remove cards from new deck that already exist in the collection.

    Args:
        new_deck_name: Name of the new deck to deduplicate
        existing_collection: Optional pre-loaded collection cards. If None, loads all cards.
        comparison_field_index: Which field index to compare (default: 0 for first field)
        custom_comparison: Optional custom comparison function

    Returns:
        Table of unique cards (cards that don't exist in collection)
    """
    # Load new deck cards
    new_cards = AnkiCardsTable.load(deck_name=new_deck_name)

    # Load existing collection if not provided
    if existing_collection is None:
        existing_collection = AnkiCardsTable.load()

    # Filter out cards from the new deck itself from existing collection
    existing_cards = existing_collection.where(lambda card: card.deck_name != new_deck_name)

    # Define comparison function
    if custom_comparison is None:

        def default_comparison(new_field: str, existing_field: str) -> bool:
            return new_field.strip().lower() == existing_field.strip().lower()

        comparison_func = default_comparison
    else:
        comparison_func = custom_comparison

    # Find unique cards (not duplicates)
    unique_cards = new_cards.where(
        lambda new_card: not existing_cards.any(
            lambda existing_card: (
                len(new_card.fields) > comparison_field_index
                and len(existing_card.fields) > comparison_field_index
                and comparison_func(
                    new_card.fields[comparison_field_index],
                    existing_card.fields[comparison_field_index],
                )
            )
        )
    )

    return Table.from_rows(list(unique_cards), AnkiCard)


def analyze_deck_overlap(deck1_name: str, deck2_name: str, comparison_field_index: int = 0) -> dict:
    """Analyze overlap between two decks.

    Args:
        deck1_name: Name of first deck
        deck2_name: Name of second deck
        comparison_field_index: Which field index to compare

    Returns:
        Dictionary with overlap statistics
    """
    deck1_cards = AnkiCardsTable.load(deck_name=deck1_name)
    deck2_cards = AnkiCardsTable.load(deck_name=deck2_name)

    # Find cards in deck1 that are also in deck2
    deck1_in_deck2 = deck1_cards.where(
        lambda card1: deck2_cards.any(
            lambda card2: (
                len(card1.fields) > comparison_field_index
                and len(card2.fields) > comparison_field_index
                and card1.fields[comparison_field_index].strip().lower()
                == card2.fields[comparison_field_index].strip().lower()
            )
        )
    )

    # Find cards in deck2 that are also in deck1
    deck2_cards.where(
        lambda card2: deck1_cards.any(
            lambda card1: (
                len(card1.fields) > comparison_field_index
                and len(card2.fields) > comparison_field_index
                and card1.fields[comparison_field_index].strip().lower()
                == card2.fields[comparison_field_index].strip().lower()
            )
        )
    )

    deck1_total = deck1_cards.count()
    deck2_total = deck2_cards.count()
    overlap_count = deck1_in_deck2.count()

    return {
        "deck1_name": deck1_name,
        "deck2_name": deck2_name,
        "deck1_total_cards": deck1_total,
        "deck2_total_cards": deck2_total,
        "overlap_cards": overlap_count,
        "deck1_unique_cards": deck1_total - overlap_count,
        "deck2_unique_cards": deck2_total - overlap_count,
        "overlap_percentage_deck1": (overlap_count / deck1_total * 100) if deck1_total > 0 else 0,
        "overlap_percentage_deck2": (overlap_count / deck2_total * 100) if deck2_total > 0 else 0,
    }
