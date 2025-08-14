"""Import cards from .apkg files."""

import json
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from tidylinq import Table

from tidyanki.models.anki_models import AnkiCard, AnkiModel, AnkiNote


def load_models_from_db(conn: sqlite3.Connection) -> dict[int, AnkiModel]:
    """Load models from any Anki database connection.

    Args:
        conn: SQLite connection to Anki database

    Returns:
        Dictionary mapping model ID to AnkiModel objects
    """
    cursor = conn.execute("SELECT models FROM col LIMIT 1")
    row = cursor.fetchone()
    models_json = row["models"]
    models_dict = json.loads(models_json)

    models = {}
    for model_id_str, model_data in models_dict.items():
        model_id = int(model_id_str)
        models[model_id] = AnkiModel(
            id=model_id,
            name=model_data["name"],
            fields=model_data["flds"],
            templates=model_data["tmpls"],
            css=model_data.get("css", ""),
            original_data=model_data,
        )

    return models


def load_notes_from_apkg(apkg_path: Path) -> Table[AnkiNote]:
    """Load notes from an .apkg file.

    Args:
        apkg_path: Path to the .apkg file to load notes from

    Returns:
        Table of AnkiNote objects from the package
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    notes = []

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

        # Connect to the database and extract notes
        with sqlite3.connect(collection_db) as conn:
            conn.row_factory = sqlite3.Row

            # Get notes directly
            cursor = conn.execute("""
                SELECT n.id, n.guid, n.mid, n.flds, n.tags
                FROM notes n
                ORDER BY n.id
            """)

            rows = cursor.fetchall()

            for row in rows:
                fields = row["flds"].split("\x1f")  # Anki field separator

                notes.append(
                    AnkiNote(
                        id=row["id"],
                        guid=row["guid"],
                        mid=row["mid"],
                        fields=fields,
                        tags=row["tags"].split() if row["tags"] else [],
                    )
                )

    return Table.from_rows(notes, AnkiNote)


def load_cards_from_apkg(apkg_path: Path) -> tuple[Table[AnkiCard], dict[int, AnkiModel]]:
    """Load cards from an .apkg file.

    Args:
        apkg_path: Path to the .apkg file to load cards from

    Returns:
        Tuple of (Table of AnkiCard objects, dict of models)
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
            row = cursor.fetchone()
            decks_json = row["decks"]
            decks_dict = json.loads(decks_json)

            # Create deck_id -> deck_name mapping
            deck_mapping = {}
            for deck_id, deck_info in decks_dict.items():
                deck_mapping[int(deck_id)] = deck_info["name"]

            # Load models using shared function
            models = load_models_from_db(conn)

            # Now get cards with deck info and model ID
            cursor = conn.execute("""
                SELECT c.id, c.did, n.flds, n.tags, c.ord, c.type, n.mid, c.nid
                FROM cards c 
                JOIN notes n ON c.nid = n.id
                ORDER BY c.id
            """)

            rows = cursor.fetchall()

            for row in rows:
                fields = row["flds"].split("\x1f")  # Anki field separator
                deck_name = deck_mapping.get(row["did"], f"Unknown Deck {row['did']}")

                model_id = row["mid"]
                model = models[model_id]

                cards.append(
                    AnkiCard(
                        id=row["id"],
                        fields=fields,
                        tags=row["tags"].split() if row["tags"] else [],
                        card_type=row["ord"],
                        deck_name=deck_name,
                        model=model,
                        note_id=row["nid"],
                    )
                )

    return Table.from_rows(cards, AnkiCard), models


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


def load_models_from_apkg(apkg_path: Path) -> dict[int, AnkiModel]:
    """Load models from an .apkg file.

    Args:
        apkg_path: Path to the .apkg file

    Returns:
        Dictionary mapping model ID to AnkiModel objects
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    models = {}

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
            # Load models using shared function
            models = load_models_from_db(conn)

    return models


def load_media_from_apkg(apkg_path: Path) -> list[str]:
    """Load list of media files from an .apkg file.

    Args:
        apkg_path: Path to the .apkg file

    Returns:
        List of media file names in the package
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    media_files = []

    with zipfile.ZipFile(apkg_path, "r") as zip_file:
        # Get all files in the ZIP, excluding the database and media mapping
        for file_info in zip_file.filelist:
            filename = file_info.filename
            # Skip database files and media mapping file
            if filename not in ["collection.anki2", "collection.anki21", "media"]:
                media_files.append(filename)

    return media_files


def extract_media_files(apkg_path: Path, dest_dir: Path) -> list[Path]:
    """Extract media files from APKG to destination directory.

    Args:
        apkg_path: Path to the .apkg file
        dest_dir: Directory to extract media files to

    Returns:
        List of paths to extracted media files
    """
    if not apkg_path.exists():
        raise FileNotFoundError(f"APKG file not found: {apkg_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = []

    with zipfile.ZipFile(apkg_path, "r") as zip_file:
        for file_info in zip_file.filelist:
            filename = file_info.filename
            # Skip database files and media mapping file
            if filename not in ["collection.anki2", "collection.anki21", "media"]:
                # Extract the file
                zip_file.extract(filename, dest_dir)
                extracted_files.append(dest_dir / filename)

    return extracted_files


def detect_media_in_fields(fields: list[str]) -> list[str]:
    """Detect media file references in card fields.

    Args:
        fields: List of field contents

    Returns:
        List of media file names referenced in the fields
    """
    media_files = []

    for field in fields:
        # Find image references: <img src="filename.jpg">
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', field, re.IGNORECASE)
        media_files.extend(img_matches)

        # Find audio references: [sound:filename.mp3]
        audio_matches = re.findall(r"\[sound:([^\]]+)\]", field, re.IGNORECASE)
        media_files.extend(audio_matches)

    return list(set(media_files))  # Remove duplicates
