"""Core functionality for tidyanki."""

from .anki_db import get_anki_db_path, setup_anki_connection
from .deduplication import analyze_deck_overlap, find_duplicate_cards, remove_duplicate_cards
from .export import export_cards_to_deck, export_deduplicated_deck, export_filtered_deck
from .operations import (
    create_vocab_cards,
    generate_example_sentence,
    get_template_content,
    get_templates,
)
from .tables import AnkiCardsTable, AnkiCardsWithStatusTable, AnkiDecksTable

__all__ = [
    "setup_anki_connection",
    "get_anki_db_path",
    "AnkiDecksTable",
    "AnkiCardsTable",
    "AnkiCardsWithStatusTable",
    "get_templates",
    "get_template_content",
    "create_vocab_cards",
    "generate_example_sentence",
    "find_duplicate_cards",
    "remove_duplicate_cards",
    "analyze_deck_overlap",
    "export_cards_to_deck",
    "export_deduplicated_deck",
    "export_filtered_deck",
]
