"""Import cards from .apkg files."""

import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from tidylinq import Table

from tidyanki.models.anki_models import AnkiCard


def load_cards_from_apkg(apkg_path: Path) -> Table[AnkiCard]:
    """Load cards from an .apkg file.

    Args:
        apkg_path: Path to the .apkg file to load cards from

    Returns:
        Table of AnkiCard objects from the package
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    cards = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Extract the .apkg file (it's a ZIP archive)
        with zipfile.ZipFile(apkg_path, "r") as zip_file:
            zip_file.extractall(temp_path)

        # Find the collection database file
        collection_db = temp_path / "collection.anki2"
        if not collection_db.exists():
            # Try alternative name
            collection_db = temp_path / "collection.anki21"
            if not collection_db.exists():
                raise ValueError(f"No Anki database found in {apkg_path}")

        # Connect to the database and extract cards
        with sqlite3.connect(collection_db) as conn:
            conn.row_factory = sqlite3.Row

            # First, get deck information from the col table
            cursor = conn.execute("SELECT decks FROM col LIMIT 1")
            decks_json = cursor.fetchone()["decks"]
            decks_dict = json.loads(decks_json)

            # Create deck_id -> deck_name mapping
            deck_mapping = {}
            for deck_id, deck_info in decks_dict.items():
                deck_mapping[int(deck_id)] = deck_info["name"]

            # Now get cards with deck info
            cursor = conn.execute("""
                SELECT c.id, c.did, n.flds, n.tags, c.ord, c.type
                FROM cards c 
                JOIN notes n ON c.nid = n.id
                ORDER BY c.id
            """)

            rows = cursor.fetchall()

            for row in rows:
                fields = row["flds"].split("\x1f")  # Anki field separator
                deck_name = deck_mapping.get(row["did"], f"Unknown Deck {row['did']}")

                cards.append(
                    AnkiCard(
                        id=row["id"],
                        fields=fields,
                        tags=row["tags"].split() if row["tags"] else [],
                        card_type=row["ord"],
                        deck_name=deck_name,
                    )
                )

    return Table.from_rows(cards, AnkiCard)


def get_apkg_deck_names(apkg_path: Path) -> list[str]:
    """Get list of deck names in an .apkg file.

    Args:
        apkg_path: Path to the .apkg file

    Returns:
        List of deck names in the package
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    deck_names = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with zipfile.ZipFile(apkg_path, "r") as zip_file:
            zip_file.extractall(temp_path)

        collection_db = temp_path / "collection.anki2"
        if not collection_db.exists():
            collection_db = temp_path / "collection.anki21"
            if not collection_db.exists():
                raise ValueError(f"No Anki database found in {apkg_path}")

        with sqlite3.connect(collection_db) as conn:
            conn.row_factory = sqlite3.Row
            # Get deck information from the col table
            cursor = conn.execute("SELECT decks FROM col LIMIT 1")
            row = cursor.fetchone()
            decks_json = row["decks"]
            decks_dict = json.loads(decks_json)

            # Extract deck names
            for deck_info in decks_dict.values():
                deck_names.append(deck_info["name"])

    return deck_names
