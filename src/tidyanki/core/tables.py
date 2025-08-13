"""Table implementations for Anki data using tidylinq."""

from __future__ import annotations

from tidylinq import Table

from tidyanki.models.anki_models import AnkiCard, AnkiCardWithStatus, AnkiDeck

from .anki_db import get_anki_db_path, setup_anki_connection


class AnkiDecksTable(Table[AnkiDeck]):
    """Table for querying Anki decks."""

    @classmethod
    def load(cls) -> Table[AnkiDeck]:
        """Load all decks from the Anki database."""
        anki_db = get_anki_db_path()
        if not anki_db:
            return cls.from_rows([], AnkiDeck)  # type: ignore[return-value]

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

        return cls.from_rows(decks, AnkiDeck)  # type: ignore[return-value]


class AnkiCardsTable(Table[AnkiCard]):
    """Table for querying Anki cards."""

    @classmethod
    def load(cls, deck_name: str | None = None, limit: int = 1000) -> Table[AnkiCard]:
        """Load cards from the Anki database.

        Args:
            deck_name: Optional deck name to filter by
            limit: Maximum number of cards to return
        """
        anki_db = get_anki_db_path()
        if not anki_db:
            return cls.from_rows([], AnkiCard)

        with setup_anki_connection(anki_db) as conn:
            sql_query = """
                SELECT c.id, n.flds, n.tags, c.ord, c.type, d.name as deck_name
                FROM cards c 
                JOIN notes n ON c.nid = n.id 
                JOIN decks d ON c.did = d.id 
            """
            params = []

            if deck_name:
                search_name = deck_name.replace("::", "\x1f")
                sql_query += " WHERE d.name = ?"
                params.append(search_name)

            sql_query += f" LIMIT {limit}"

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
                    )
                )

        return cls.from_rows(cards, AnkiCard)

    @classmethod
    def search(cls, query: str, deck_name: str | None = None, limit: int = 100) -> Table[AnkiCard]:
        """Search for cards by query text.

        Args:
            query: Search query to find in note fields
            deck_name: Optional deck name to filter by
            limit: Maximum number of cards to return
        """
        anki_db = get_anki_db_path()
        if not anki_db:
            return cls.from_rows([], AnkiCard)

        with setup_anki_connection(anki_db) as conn:
            sql_query = """
              SELECT n.id, n.flds, n.tags, c.ord, d.name as deck_name
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

            sql_query += f" LIMIT {limit}"

            cursor = conn.execute(sql_query, params)
            rows = cursor.fetchall()

            cards = []
            for row in rows:
                fields = row["flds"].split("\x1f")  # Anki field separator
                deck_name = row["deck_name"].replace("\x1f", "::")  # Format deck name
                cards.append(
                    AnkiCard(
                        id=row["id"],
                        fields=fields,
                        tags=row["tags"].split() if row["tags"] else [],
                        card_type=row["ord"],
                        deck_name=deck_name,
                    )
                )

        return cls.from_rows(cards, AnkiCard)


class AnkiCardsWithStatusTable(Table[AnkiCardWithStatus]):
    """Table for querying Anki cards with study status."""

    @classmethod
    def load(cls, deck_name: str | None = None, limit: int = 100) -> Table[AnkiCardWithStatus]:
        """Load cards with study status.

        Args:
            deck_name: Optional deck name to filter by
            limit: Maximum number of cards to return
        """
        anki_db = get_anki_db_path()
        if not anki_db:
            return cls.from_rows([], AnkiCardWithStatus)

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

            sql_query += f" ORDER BY c.due LIMIT {limit}"

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

        return cls.from_rows(cards, AnkiCardWithStatus)
