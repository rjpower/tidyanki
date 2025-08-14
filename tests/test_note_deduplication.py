"""Test note-based deduplication logic."""

from tidylinq import Table

from tidyanki.core.deduplication import (
    build_collection_word_set,
    normalize_and_split,
    notes_match_auto,
)
from tidyanki.models.anki_models import AnkiNote


def test_normalize_and_split():
    """Test text normalization and splitting."""
    # Test basic splitting
    result = normalize_and_split("apple, banana; cherry|grape")
    expected = {"apple", "banana", "cherry", "grape"}
    assert result == expected

    # Test HTML tag removal - should treat as single item since no delimiters
    result = normalize_and_split("<b>bold</b> text with <i>italics</i>")
    expected = set()  # Exceeds max word length (20 chars)
    assert result == expected

    # Test HTML tag removal with delimiters
    result = normalize_and_split("<b>bold</b>, text with <i>italics</i>")
    expected = {"bold", "text with italics"}
    assert result == expected

    # Test ignored words
    result = normalize_and_split("item, sentence, plain, valid")
    expected = {"valid"}
    assert result == expected

    # Test max word length filtering - no delimiters means treated as one long item
    result = normalize_and_split("short verylongwordthatexceedslimit normal", max_word_length=10)
    expected = set()  # The whole string exceeds max length since no delimiters
    assert result == expected

    # Test max word length filtering with delimiters
    result = normalize_and_split("short, verylongwordthatexceedslimit, normal", max_word_length=10)
    expected = {"short", "normal"}  # Long word filtered out
    assert result == expected


def test_build_collection_word_set():
    """Test building word set from notes collection."""
    notes = [
        AnkiNote(id=1, guid="guid1", mid=123, fields=["apple pie", "red fruit"], tags=[]),
        AnkiNote(id=2, guid="guid2", mid=123, fields=["banana split", "yellow fruit"], tags=[]),
    ]
    collection = Table.from_rows(notes, AnkiNote)

    word_set = build_collection_word_set(collection)
    expected = {"apple pie", "red fruit", "banana split", "yellow fruit"}
    assert word_set == expected


def test_notes_match_auto():
    """Test automatic note matching using word intersection."""
    # Create collection word set
    collection_words = {"apple", "pie", "red", "fruit", "banana"}

    # Test matching note
    matching_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["apple", "green fruit"], tags=[])
    assert notes_match_auto(matching_note, collection_words) is True

    # Test non-matching note
    non_matching_note = AnkiNote(
        id=2, guid="guid2", mid=123, fields=["orange juice", "citrus drink"], tags=[]
    )
    assert notes_match_auto(non_matching_note, collection_words) is False


def test_notes_match_auto_with_ignored_words():
    """Test that ignored words don't cause false matches."""
    collection_words = {"apple", "pie"}

    # Note with only ignored words shouldn't match
    note_with_ignored = AnkiNote(
        id=1, guid="guid1", mid=123, fields=["item", "sentence", "plain"], tags=[]
    )
    assert notes_match_auto(note_with_ignored, collection_words) is False


def test_empty_fields_handling():
    """Test handling of notes with empty fields."""
    collection_words = {"apple", "pie"}

    empty_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["", ""], tags=[])
    assert notes_match_auto(empty_note, collection_words) is False


def test_case_insensitive_matching():
    """Test that matching is case insensitive."""
    collection_words = {"apple", "pie"}

    mixed_case_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["APPLE", "PIE"], tags=[])
    assert notes_match_auto(mixed_case_note, collection_words) is True
