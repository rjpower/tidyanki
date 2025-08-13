"""TidyAnki - Tools for working with Anki collections and decks."""

from tidyanki.core import *
from tidyanki.models import *

__all__ = [
    # Tables
    "AnkiDecksTable",
    "AnkiCardsTable",
    "AnkiCardsWithStatusTable",
    # Models
    "AnkiDeck",
    "AnkiCard",
    "AnkiCardWithStatus",
    "AnkiTemplate",
    "AnkiTemplateContent",
    "AddVocabCardRequest",
    "AddVocabCardsRequest",
    "AnkiCreateResult",
    "ExampleSentenceResponse",
    # Operations
    "get_templates",
    "get_template_content",
    "create_vocab_cards",
    "generate_example_sentence",
    # Deduplication
    "find_duplicate_cards",
    "remove_duplicate_cards",
    "analyze_deck_overlap",
    # Export
    "export_cards_to_deck",
    "export_deduplicated_deck",
    "export_filtered_deck",
    # Database
    "setup_anki_connection",
    "get_anki_db_path",
]
