"""Core functionality for tidyanki."""

from .anki_db import get_anki_db_path, setup_anki_connection
from .deduplication import analyze_deck_overlap, deduplicate_external_deck, remove_duplicate_notes
from .export import export_notes_to_deck
from .operations import (
    create_vocab_cards,
    generate_example_sentence,
    get_template_content,
    get_templates,
)
from .tables import load_cards, load_cards_with_status, load_decks, load_notes, search_cards

__all__ = [
    "setup_anki_connection",
    "get_anki_db_path",
    "load_decks",
    "load_cards",
    "load_cards_with_status",
    "load_notes",
    "search_cards",
    "get_templates",
    "get_template_content",
    "create_vocab_cards",
    "generate_example_sentence",
    "remove_duplicate_notes",
    "deduplicate_external_deck",
    "analyze_deck_overlap",
    "export_notes_to_deck",
]
