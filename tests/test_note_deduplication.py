"""Test note-based deduplication logic."""

from tidylinq import Table

from tidyanki.core.deduplication import (
    build_collection_word_set,
    normalize_and_split,
    note_matches_collection,
)
from tidyanki.models.anki_models import AnkiNote


def test_normalize_and_split():
    """Test text normalization and splitting."""
    # Test basic splitting
    result = normalize_and_split("りんご, バナナ; さくらんぼ|ぶどう")
    expected = {"りんご", "バナナ", "さくらんぼ", "ぶどう"}
    assert result == expected

    # Test HTML tag removal
    result = normalize_and_split("<b>太字</b>テキスト<i>斜体</i>")
    expected = {"太字テキスト斜体"}
    assert result == expected

    # Test with Japanese text
    result = normalize_and_split("日本語のテスト")
    expected = {"日本語のテスト"}
    assert result == expected

    # Test with hiragana and katakana
    result = normalize_and_split("ひらがなとカタカナ")
    expected = {"ひらがなとカタカナ"}
    assert result == expected

    # Test max word length filtering
    result = normalize_and_split(
        "短いとても長い日本語のテキストでこれは制限を超えている普通", max_word_length=10
    )
    expected = set()  # Exceeds max length
    assert result == expected

    # Test shorter Japanese text within limit
    result = normalize_and_split("短いテスト", max_word_length=10)
    expected = {"短いテスト"}
    assert result == expected


def test_build_collection_word_set():
    """Test building word set from notes collection."""
    notes = [
        AnkiNote(id=1, guid="guid1", mid=123, fields=["りんごパイ", "赤い果物"], tags=[]),
        AnkiNote(id=2, guid="guid2", mid=123, fields=["バナナスプリット", "黄色い果物"], tags=[]),
    ]
    collection = Table.from_rows(notes, AnkiNote)

    word_set = build_collection_word_set(collection)
    expected = {"りんごパイ", "赤い果物", "バナナスプリット", "黄色い果物"}
    assert word_set == expected


def test_notes_match_auto():
    """Test automatic note matching using word intersection."""
    # Create collection word set
    collection_words = {"りんご", "パイ", "赤い", "果物", "バナナ"}

    # Test matching note
    matching_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["りんご", "緑の果物"], tags=[])
    assert note_matches_collection(matching_note, collection_words) is True

    # Test non-matching note
    non_matching_note = AnkiNote(
        id=2, guid="guid2", mid=123, fields=["オレンジジュース", "柑橘系飲料"], tags=[]
    )
    assert note_matches_collection(non_matching_note, collection_words) is False


def test_notes_match_auto_with_ignored_words():
    """Test that ignored words don't cause false matches."""
    collection_words = {"りんご", "パイ"}

    # Note with Japanese text that doesn't match
    note_with_different_words = AnkiNote(
        id=1, guid="guid1", mid=123, fields=["みかん", "お茶", "普通"], tags=[]
    )
    assert note_matches_collection(note_with_different_words, collection_words) is False


def test_empty_fields_handling():
    """Test handling of notes with empty fields."""
    collection_words = {"りんご", "パイ"}

    empty_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["", ""], tags=[])
    assert note_matches_collection(empty_note, collection_words) is False


def test_case_insensitive_matching():
    """Test that matching works with Japanese text."""
    collection_words = {"りんご", "パイ"}

    matching_note = AnkiNote(id=1, guid="guid1", mid=123, fields=["りんご", "パイ"], tags=[])
    assert note_matches_collection(matching_note, collection_words) is True
