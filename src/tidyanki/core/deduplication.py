"""Deck deduplication functionality."""

import logging
import re
from collections.abc import Callable
from pathlib import Path

from tidylinq import Table

from tidyanki.core.import_apkg import load_notes_from_apkg
from tidyanki.core.tables import load_notes
from tidyanki.models.anki_models import AnkiNote

IGNORED_WORDS = {"item", "sentence", "plain", "verb"}


logger = logging.getLogger(__name__)


def is_japanese(text: str) -> bool:
    """Check if the text contains Japanese characters."""
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


def normalize_and_split(text: str, max_word_length: int = 20) -> set[str]:
    """Normalize text and split into words for comparison.

    Args:
        text: Input text to normalize and split
        max_word_length: Maximum word length to include (filters out sentences)

    Returns:
        Set of normalized words
    """
    if not is_japanese(text):
        return set()

    text = re.sub(r"<[^>]+>", "", text)
    words = re.split(r"[,;|]", text.lower().strip())
    words = [word.strip() for word in words if word.strip()]
    words = [word for word in words if word not in IGNORED_WORDS]
    return {word for word in words if len(word) <= max_word_length}


def build_collection_word_set(collection: Table[AnkiNote]) -> set[str]:
    """Build a set of all words from collection notes.

    Args:
        collection: Table of collection notes

    Returns:
        Set of all words found in collection note fields
    """
    word_set = set()
    for note in collection:
        for field in note.fields:
            word_set.update(normalize_and_split(field))
    return word_set


def note_matches_collection(external_note: AnkiNote, collection_word_set: set[str]) -> bool:
    """Check if note matches any collection notes using word intersection.

    Args:
        external_note: Note from external deck
        collection_word_set: Set of all words from collection notes

    Returns:
        True if note has word overlap with collection
    """
    for field in external_note.fields:
        intersection = normalize_and_split(field).intersection(collection_word_set)
        if intersection:
            # logger.info(f"Match for note {external_note.fields} against fields {intersection}")
            return True

    return False


def analyze_deck_overlap(deck1_name: str, deck2_name: str, comparison_field_index: int = 0) -> dict:
    """Analyze overlap between two decks based on notes.

    Args:
        deck1_name: Name of first deck
        deck2_name: Name of second deck
        comparison_field_index: Which field index to compare

    Returns:
        Dictionary with overlap statistics
    """
    deck1_notes = load_notes(deck_name=deck1_name)
    deck2_notes = load_notes(deck_name=deck2_name)

    # Find notes in deck1 that are also in deck2
    deck1_in_deck2 = deck1_notes.where(
        lambda note1: deck2_notes.any(
            lambda note2: (
                len(note1.fields) > comparison_field_index
                and len(note2.fields) > comparison_field_index
                and note1.fields[comparison_field_index].strip().lower()
                == note2.fields[comparison_field_index].strip().lower()
            )
        )
    )

    # Find notes in deck2 that are also in deck1
    deck2_notes.where(
        lambda note2: deck1_notes.any(
            lambda note1: (
                len(note1.fields) > comparison_field_index
                and len(note2.fields) > comparison_field_index
                and note1.fields[comparison_field_index].strip().lower()
                == note2.fields[comparison_field_index].strip().lower()
            )
        )
    )

    deck1_total = deck1_notes.count()
    deck2_total = deck2_notes.count()
    overlap_count = deck1_in_deck2.count()

    return {
        "deck1_name": deck1_name,
        "deck2_name": deck2_name,
        "deck1_total_notes": deck1_total,
        "deck2_total_notes": deck2_total,
        "overlap_notes": overlap_count,
        "deck1_unique_notes": deck1_total - overlap_count,
        "deck2_unique_notes": deck2_total - overlap_count,
        "overlap_percentage_deck1": (overlap_count / deck1_total * 100) if deck1_total > 0 else 0,
        "overlap_percentage_deck2": (overlap_count / deck2_total * 100) if deck2_total > 0 else 0,
    }


def deduplicate_external_deck(
    apkg_path: Path,
    existing_collection: Table[AnkiNote],
) -> Table[AnkiNote]:
    """Remove notes from external .apkg file that already exist in the collection.

    Args:
        apkg_path: Path to the .apkg file to deduplicate
        existing_collection: Optional pre-loaded collection notes. If None, loads all notes.

    Returns:
        Table of unique notes (notes that don't exist in collection)
    """
    # Load notes from .apkg file
    external_notes = load_notes_from_apkg(apkg_path)
    collection_word_set = build_collection_word_set(existing_collection)

    # Find unique notes (not duplicates) using word intersection
    unique_notes = external_notes.where(
        lambda external_note: not note_matches_collection(external_note, collection_word_set)
    ).materialize()

    logger.info(
        f"Kept {len(unique_notes)} unique notes out of {len(external_notes)} from {apkg_path}"
    )

    # dropped_notes = external_notes.where(
    #     lambda external_note: note_matches_collection(external_note, collection_word_set)
    # )

    # for note in dropped_notes:
    #     logger.info(f"Dropping note ID {note.id} with fields: {note.fields[3]}")
    return unique_notes
