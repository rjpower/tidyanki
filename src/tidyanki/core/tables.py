"""Functions for loading Anki data using tidylinq."""

from __future__ import annotations

from tidylinq import Table

from tidyanki.core.anki_db import get_anki_db_path, setup_anki_connection
from tidyanki.models.anki_models import AnkiCard, AnkiCardWithStatus, AnkiDeck, AnkiNote


def load_decks() -> Table[AnkiDeck]:
    """Load all decks from the Anki database."""
    anki_db = get_anki_db_path()
    if not anki_db:
        return Table.from_rows([], AnkiDeck)

    with setup_anki_connection(anki_db) as conn:
        cursor = conn.execute(
            """
            SELECT d.name as deck_name, 
                   COUNT(c.id) as card_count,
                   d.id as deck_id
            FROM decks d
            LEFT JOIN cards c ON c.did = d.id
            GROUP BY d.id, d.name
            ORDER BY d.name COLLATE unicase
        """
        )
        rows = cursor.fetchall()

        decks = []
        for row in rows:
            deck_name = row["deck_name"].replace(
                "\x1f", "::"
            )  # Replace hierarchy separator with ::
            decks.append(
                AnkiDeck(
                    name=deck_name,
                    card_count=row["card_count"],
                    deck_id=row["deck_id"],
                )
            )

    return Table.from_rows(decks, AnkiDeck)


def load_notes(deck_name: str | None = None) -> Table[AnkiNote]:
    """Load notes from the Anki database.

    Args:
        deck_name: Optional deck name to filter by
    """
    anki_db = get_anki_db_path()
    if not anki_db:
        return Table.from_rows([], AnkiNote)

    with setup_anki_connection(anki_db) as conn:
        sql_query = """
            SELECT DISTINCT n.id, n.guid, n.mid, n.flds, n.tags
            FROM notes n
        """
        params = []

        if deck_name:
            search_name = deck_name.replace("::", "\x1f")
            sql_query += """
                JOIN cards c ON c.nid = n.id 
                JOIN decks d ON c.did = d.id 
                WHERE d.name = ?
            """
            params.append(search_name)

        cursor = conn.execute(sql_query, params)
        rows = cursor.fetchall()

        notes = []
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


def load_cards(deck_name: str | None = None) -> Table[AnkiCard]:
    """Load cards from the Anki database.

    Args:
        deck_name: Optional deck name to filter by
    """
    anki_db = get_anki_db_path()
    if not anki_db:
        return Table.from_rows([], AnkiCard)

    with setup_anki_connection(anki_db) as conn:
        sql_query = """
            SELECT c.id, n.flds, n.tags, c.ord, c.type, d.name as deck_name, n.mid, c.nid
            FROM cards c 
            JOIN notes n ON c.nid = n.id 
            JOIN decks d ON c.did = d.id 
        """
        params = []

        if deck_name:
            search_name = deck_name.replace("::", "\x1f")
            sql_query += " WHERE d.name = ?"
            params.append(search_name)

        cursor = conn.execute(sql_query, params)
        rows = cursor.fetchall()

        cards = []
        for row in rows:
            fields = row["flds"].split("\x1f")  # Anki field separator
            deck_name_formatted = row["deck_name"].replace("\x1f", "::")

            cards.append(
                AnkiCard(
                    id=row["id"],
                    fields=fields,
                    tags=row["tags"].split() if row["tags"] else [],
                    card_type=row["ord"],
                    deck_name=deck_name_formatted,
                    model=None,
                    note_id=row["nid"],
                )
            )

    return Table.from_rows(cards, AnkiCard)


def search_cards(query: str, deck_name: str | None = None) -> Table[AnkiCard]:
    """Search for cards by query text.

    Args:
        query: Search query to find in note fields
        deck_name: Optional deck name to filter by
    """
    anki_db = get_anki_db_path()
    if not anki_db:
        return Table.from_rows([], AnkiCard)

    with setup_anki_connection(anki_db) as conn:
        sql_query = """
          SELECT c.id, n.flds, n.tags, c.ord, d.name as deck_name, n.mid, c.nid
          FROM notes n
          JOIN cards c ON c.nid = n.id
          JOIN decks d ON c.did = d.id
          WHERE n.flds LIKE ?
      """
        params = [f"%{query}%"]

        if deck_name:
            search_name = deck_name.replace("::", "\x1f")
            sql_query += " AND d.name = ?"
            params.append(search_name)

        cursor = conn.execute(sql_query, params)
        rows = cursor.fetchall()

        cards = []
        for row in rows:
            fields = row["flds"].split("\x1f")  # Anki field separator
            deck_name_formatted = row["deck_name"].replace("\x1f", "::")  # Format deck name

            cards.append(
                AnkiCard(
                    id=row["id"],
                    fields=fields,
                    tags=row["tags"].split() if row["tags"] else [],
                    card_type=row["ord"],
                    deck_name=deck_name_formatted,
                    model=None,
                    note_id=row["nid"],
                )
            )

    return Table.from_rows(cards, AnkiCard)


def load_cards_with_status(deck_name: str | None = None) -> Table[AnkiCardWithStatus]:
    """Load cards with study status.

    Args:
        deck_name: Optional deck name to filter by
    """
    anki_db = get_anki_db_path()
    if not anki_db:
        return Table.from_rows([], AnkiCardWithStatus)

    with setup_anki_connection(anki_db) as conn:
        sql_query = """
            SELECT c.id, c.type, c.queue, c.due, c.reps, c.lapses, c.factor, d.name as deck_name
            FROM cards c 
            JOIN decks d ON c.did = d.id
        """
        params = []

        if deck_name:
            search_name = deck_name.replace("::", "\x1f")
            sql_query += " WHERE d.name = ?"
            params.append(search_name)

        sql_query += " ORDER BY c.due"

        cursor = conn.execute(sql_query, params)
        rows = cursor.fetchall()

        cards = []
        for row in rows:
            deck_name_formatted = row["deck_name"].replace("\x1f", "::")
            cards.append(
                AnkiCardWithStatus(
                    id=row["id"],
                    type=row["type"],
                    queue=row["queue"],
                    due=row["due"],
                    reps=row["reps"],
                    lapses=row["lapses"],
                    factor=row["factor"],
                    deck_name=deck_name_formatted,
                )
            )

    return Table.from_rows(cards, AnkiCardWithStatus)
