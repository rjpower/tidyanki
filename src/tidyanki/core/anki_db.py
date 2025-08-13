"""Database connection utilities for Anki."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from unidecode import unidecode


def unicase_compare(x, y):
    """Custom collation function for unicase comparison."""
    x_ = unidecode(x).lower()
    y_ = unidecode(y).lower()
    return 1 if x_ > y_ else -1 if x_ < y_ else 0


@contextmanager
def setup_anki_connection(anki_db_path):
    """Set up SQLite connection with custom collations for Anki database."""
    conn = sqlite3.connect(str(anki_db_path))
    conn.row_factory = sqlite3.Row
    conn.create_collation("unicase", unicase_compare)
    try:
        yield conn
    finally:
        conn.close()


def get_anki_db_path() -> Path | None:
    """Get Anki database path."""
    # Check current directory first
    local_db = Path("anki.db")
    if local_db.exists():
        return local_db

    # Then check common Anki locations
    anki_base = Path.home() / "Library" / "Application Support" / "Anki2"
    if anki_base.exists():
        for profile_dir in anki_base.iterdir():
            if profile_dir.is_dir():
                collection = profile_dir / "collection.anki2"
                if collection.exists():
                    return collection
    return None
