"""Import cards from .apkg files."""

import json
import logging
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from tidylinq import Table

from tidyanki.models.anki_models import AnkiModel, AnkiNote, MediaFile

logger = logging.getLogger(__name__)


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
    """Load notes from an .apkg file with models and media references attached.

    Args:
        apkg_path: Path to the .apkg file to load notes from

    Returns:
        Table of AnkiNote objects from the package with full model and media info
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

        # Connect to the database and extract notes
        with sqlite3.connect(collection_db) as conn:
            conn.row_factory = sqlite3.Row

            # Load models first
            models = load_models_from_db(conn)

            # Get notes directly
            cursor = conn.execute("""
                SELECT n.id, n.guid, n.mid, n.flds, n.tags
                FROM notes n
                ORDER BY n.id
            """)

            rows = cursor.fetchall()

            # Load media files from ZIP into memory
            # mapping from disk filename to media ID
            media_mapping: dict[str, str] = json.loads((temp_path / "media").read_text())
            media_data = {}
            with zipfile.ZipFile(apkg_path, "r") as zip_file:
                for file_info in zip_file.filelist:
                    filename = file_info.filename
                    if filename not in ["collection.anki2", "collection.anki21", "media"]:
                        media_data[media_mapping[filename]] = zip_file.read(filename)

            for row in rows:
                fields = row["flds"].split("\x1f")  # Anki field separator
                model_id = row["mid"]
                model = models[model_id]
                media_filenames = detect_media_in_fields(fields)

                # Create MediaFile objects with actual data
                media_files = []
                for filename in media_filenames:
                    if filename in media_data:
                        media_files.append(MediaFile(filename=filename, data=media_data[filename]))
                    else:
                        logger.warning(f"Media file not found: {filename}")

                notes.append(
                    AnkiNote(
                        id=row["id"],
                        guid=row["guid"],
                        mid=model_id,
                        fields=fields,
                        tags=row["tags"].split() if row["tags"] else [],
                        model=model,
                        media_files=media_files,
                    )
                )

    return Table.from_rows(notes, AnkiNote)


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
