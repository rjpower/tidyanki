"""Anki flashcard management tool."""

import hashlib
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import genanki
from pydantic import BaseModel, Field
from unidecode import unidecode


# Table implementation for returning data
class Table:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
    
    @classmethod
    def from_rows(cls, objects: list[BaseModel]) -> "Table":
        return cls([obj.model_dump() for obj in objects])
    
    @classmethod
    def empty(cls) -> "Table":
        return cls([])
    
    def __repr__(self):
        return f"Table({len(self.rows)} rows)"

# Simple register decorator
def register():
    def decorator(func):
        return func
    return decorator


# Local config and context stubs
class _AnkiConfig:
    """Local config for Anki operations."""
    
    def __init__(self):
        self.fast_model = "gemini/gemini-2.5-flash"
        self.slow_model = "gemini/gemini-2.5-pro"
    
    def find_anki_db(self) -> Path | None:
        """Find Anki database path."""
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


class _AnkiContext:
    """Local context for Anki operations."""
    
    def __init__(self):
        self.config = _AnkiConfig()


# Global instances
_CONFIG = _AnkiConfig()
_CONTEXT = _AnkiContext()



class SimpleConfig:
    """Simple config for Anki database location."""
    
    def find_anki_db(self) -> Path | None:
        """Find Anki database path."""
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


def get_anki_db() -> Path | None:
    """Get Anki database path."""
    config = SimpleConfig()
    return config.find_anki_db()


class AnkiListResult(BaseModel):
    """Result of listing Anki decks."""

    decks: list[dict[str, Any]]
    count: int


class AnkiCreateResult(BaseModel):
    """Result of creating Anki cards."""

    deck_path: Path
    cards_created: int
    message: str = ""


class AnkiCard(BaseModel):
    """Represents an Anki card from the database."""

    id: int
    fields: list[str]
    tags: list[str]
    card_type: int
    deck_name: str


class AnkiDeck(BaseModel):
    """Represents an Anki deck."""

    name: str
    card_count: int
    deck_id: int


class AnkiTemplate(BaseModel):
    """Represents an Anki card template."""
    
    name: str
    notetype_name: str
    notetype_id: int


class AnkiCardWithStatus(BaseModel):
    """Represents an Anki card with study status."""
    
    id: int
    type: int  # 0=new, 1=learning, 2=review, 3=relearning
    queue: int  # -1=suspended, 0=new, 1=learning, 2=review, 3=day_learn_relearn
    due: int
    reps: int
    lapses: int
    factor: int
    deck_name: str


class AnkiTemplateContent(BaseModel):
    """Represents template content with HTML."""
    
    name: str
    notetype_name: str
    front_html: str
    back_html: str
    browser_question: str


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


class AddVocabCardRequest(BaseModel):
    """Request to add a bilingual vocabulary card with audio."""

    template_name: str = Field(description="Anki card template to use.")
    term_en: str = Field(description="English term")
    term_ja: str = Field(description="Japanese term")
    reading_ja: str = Field(default="", description="Japanese reading (hiragana/katakana)")
    sentence_en: str = Field(description="English example sentence")
    sentence_ja: str = Field(description="Japanese example sentence")
    audio_en: Path | None = Field(None, description="Path to English audio file")
    audio_ja: Path | None = Field(None, description="Path to Japanese audio file")


class AddVocabCardsRequest(BaseModel):
    """Request to add multiple bilingual vocabulary cards with audio."""

    cards: list[AddVocabCardRequest] = Field(description="List of vocabulary cards to add")
    deck_name: str = Field(description="Name of the Anki deck")


class ExampleSentenceResponse(BaseModel):
    """Response model for generated example sentences."""

    source_sentence: str
    target_sentence: str


def generate_example_sentence(
    word: str,
    translation: str,
    source_language: str = "en",
    target_language: str = "ja",
    difficulty: str = "intermediate",
) -> ExampleSentenceResponse:
    """Generate example sentences for a vocabulary word using LLM.

    Args:
        word: The vocabulary word
        translation: Translation of the word
        source_language: Source language code
        target_language: Target language code
        difficulty: Difficulty level (beginner, intermediate, advanced)

    Returns:
        Tuple of (source_sentence, target_sentence)

    Example usage: generate_example_sentence("hello", "こんにちは", "en", "ja")
    """
    from tidyschema.adapters.llm import completion_with_schema
    
    prompt = f"""Create example sentences for the vocabulary word "{word}" (translation: "{translation}").

Requirements:
- Create one natural example sentence in {source_language} using the word "{word}"
- Translate that sentence to {target_language}
- Use {difficulty} level vocabulary and grammar
- Make the sentences practical and commonly used
- Keep sentences concise (under 20 words)

Return only a JSON object with this format:
{{
    "source_sentence": "The example sentence in {source_language}",
    "target_sentence": "The translation in {target_language}"
}}"""

    return completion_with_schema(
        model=_CONFIG.fast_model,
        messages=[{"role": "user", "content": prompt}],
        response_schema=ExampleSentenceResponse,
    )


@register()
def anki_list_templates() -> Table:
    """List all card templates with their note types.
    
    Example usage: anki_list_templates()
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return Table.empty()

    with setup_anki_connection(anki_db) as conn:
        cursor = conn.execute(
            """
            SELECT t.name as template_name, 
                   nt.name as notetype_name, 
                   t.ntid as notetype_id
            FROM templates t 
            JOIN notetypes nt ON t.ntid = nt.id 
            ORDER BY nt.name, t.ord
            """
        )
        rows = cursor.fetchall()

        templates = []
        for row in rows:
            templates.append(
                AnkiTemplate(
                    name=row["template_name"],
                    notetype_name=row["notetype_name"],
                    notetype_id=row["notetype_id"],
                )
            )

    return Table.from_rows(templates)


def _decode_template_config(config_blob: bytes) -> tuple[str, str, str]:
    """Decode template config from binary protobuf format.
    
    Returns tuple of (front_html, back_html, browser_question)
    """
    try:
        # The config is stored as protobuf with field tags
        # Field 1: question/front HTML
        # Field 2: answer/back HTML  
        # Field 3: browser question HTML
        
        # Simple protobuf parsing for these string fields
        config_str = config_blob.decode('utf-8', errors='ignore')
        
        # Extract strings between protobuf delimiters
        parts = []
        i = 0
        while i < len(config_str):
            if ord(config_str[i]) == 0x0a:  # String field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i:i+length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            elif ord(config_str[i]) == 0x12:  # Another string field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i:i+length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            elif ord(config_str[i]) == 0x1a:  # Third string field marker
                i += 1
                if i < len(config_str):
                    length = ord(config_str[i])
                    i += 1
                    if i + length <= len(config_str):
                        part = config_str[i:i+length]
                        parts.append(part.strip())
                        i += length
                    else:
                        break
                else:
                    break
            else:
                i += 1
        
        # Ensure we have at least 3 parts
        while len(parts) < 3:
            parts.append("")
            
        return parts[0], parts[1], parts[2]
        
    except Exception:
        return "", "", ""


@register()
def anki_get_template_content(template_name: str, notetype_name: str) -> AnkiTemplateContent | None:
    """Get HTML content for a specific template.
    
    Args:
        template_name: Name of the template
        notetype_name: Name of the note type
    
    Example usage: anki_get_template_content("Japanese to English", "Japanese Vocabulary")
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return None

    with setup_anki_connection(anki_db) as conn:
        cursor = conn.execute(
            """
            SELECT t.name as template_name, 
                   nt.name as notetype_name, 
                   t.config
            FROM templates t 
            JOIN notetypes nt ON t.ntid = nt.id 
            WHERE t.name = ? AND nt.name = ?
            """,
            (template_name, notetype_name)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
            
        front_html, back_html, browser_question = _decode_template_config(row["config"])
        
        return AnkiTemplateContent(
            name=row["template_name"],
            notetype_name=row["notetype_name"],
            front_html=front_html,
            back_html=back_html,
            browser_question=browser_question,
        )


@register()
def anki_list_cards_by_deck(deck_name: str, limit: int = 100) -> Table:
    """List cards in a specific deck with their content.
    
    Args:
        deck_name: Name of the deck to list cards from
        limit: Maximum number of cards to return (default: 100)
    
    Example usage: anki_list_cards_by_deck("Japanese Vocabulary", 50)
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return Table.empty()

    with setup_anki_connection(anki_db) as conn:
        # Convert :: to \x1f for internal Anki format
        search_name = deck_name.replace("::", "\x1f")
        
        cursor = conn.execute(
            """
            SELECT c.id, n.flds, n.tags, c.ord, c.type, d.name as deck_name
            FROM cards c 
            JOIN notes n ON c.nid = n.id 
            JOIN decks d ON c.did = d.id 
            WHERE d.name = ? 
            LIMIT ?
            """,
            (search_name, limit)
        )
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
        
    return Table.from_rows(cards)


@register()
def anki_get_study_status(deck_name: str | None = None, limit: int = 100) -> Table:
    """Get detailed study status for cards.
    
    Args:
        deck_name: Optional deck name to filter by
        limit: Maximum number of cards to return (default: 100)
    
    Example usage: anki_get_study_status("Japanese Vocabulary", 50)
    Example for all decks: anki_get_study_status()
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return Table.empty()

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
        
    return Table.from_rows(cards)


@register()
def anki_add_cards(
    deck_name: str,
    cards: list[AddVocabCardRequest],
) -> AnkiCreateResult:
    """Create multiple bilingual vocabulary cards with audio and add to Anki deck.

    Args:
        deck_name: Name of the Anki deck
        cards: List of vocabulary cards to add

    Example usage: anki_add_vocab_cards("My Deck", [card1, card2, ...])
    """
    # Generate deck ID from name
    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    # Create temporary directory for media files
    temp_dir = tempfile.TemporaryDirectory()
    media_files = []

    def _add_audio(audio_path: Path, term: str) -> str:
        """Add audio file to package with content-based filename."""
        if not audio_path or not audio_path.exists():
            return ""

        # Create a unique filename based on content hash
        audio_filename = f"audio_{hashlib.md5(term.encode()).hexdigest()[:8]}.mp3"
        temp_audio_path = Path(temp_dir.name) / audio_filename
        shutil.copy2(audio_path, temp_audio_path)
        media_files.append(temp_audio_path)

        return f"[sound:{audio_filename}]"

    # Process each card
    for card in cards:
        # Handle audio files
        term_audio_field = _add_audio(card.audio_ja, card.term_ja)
        meaning_audio_field = _add_audio(card.audio_en, card.term_en)

        # Note: This function needs to be updated to use user-selected templates
        # For now, this is a placeholder that would need template selection
        note = genanki.Note(
            model=None,  # Would be user-selected template
            fields=[
                card.term_ja,  # Term
                card.reading_ja,  # Reading
                card.term_en,  # Meaning
                card.sentence_ja,  # Example
                card.sentence_en,  # ExampleTranslation
                term_audio_field,  # TermAudio
                meaning_audio_field,  # MeaningAudio
            ],
        )
        deck.add_note(note)

    # Determine output path in temp directory
    output_temp_dir = Path(tempfile.gettempdir())
    output_path = output_temp_dir / f"{deck_name.replace(' ', '_')}_vocab.apkg"

    # Create package with media files
    package = genanki.Package(deck)
    if media_files:
        package.media_files = media_files

    try:
        package.write_to_file(str(output_path))

        return AnkiCreateResult(
            deck_path=output_path,
            cards_created=len(cards),
            message=f"Created {len(cards)} bilingual vocab cards in deck '{deck_name}'",
        )
    finally:
        # Clean up temporary directory
        temp_dir.cleanup()


@register()
def anki_add_vocab_card(req: AddVocabCardRequest) -> AnkiCreateResult:
    """Create a bilingual vocabulary card with audio and add to Anki deck.

    Example usage: anki_add_vocab_card(AddVocabCardRequest(...))
    """
    # Use the batch function with a single card
    return anki_add_cards(deck_name="Japanese Vocabulary", cards=[req])


@register()
def anki_query(query: str, limit: int = 100, deck_name: str | None = None) -> Table:
    """Search for notes in Anki database by query text.

    Args:
        query: Search query to find in note fields
        limit: Maximum number of cards to return (default: 100)
        deck_name: Optional deck name to filter by

    Example usage: anki_query("health", 50)
    Example with deck filter: anki_query("health", 20, "Japanese Vocabulary::N5")
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return Table.empty()

    with setup_anki_connection(anki_db) as conn:
        # Build query to search in note fields
        sql_query = """
          SELECT n.id, n.flds, n.tags, c.ord, d.name as deck_name
          FROM notes n
          JOIN cards c ON c.nid = n.id
          JOIN decks d ON c.did = d.id
          WHERE n.flds LIKE ?
      """
        params = [f"%{query}%"]

        # Optional deck filter
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
        return Table.from_rows(cards)


@register()
def anki_list() -> Table:
    """List all available Anki decks with their card counts (alias for anki_list).

    Example usage: anki_decks()
    """
    anki_db = _CONFIG.find_anki_db()
    if not anki_db:
        return Table.empty()

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

    return Table.from_rows(decks)


if __name__ == "__main__":
    # Simple test runner for the new functions
    print("Testing Anki functions...")
    
    print("\n1. List templates:")
    templates = anki_list_templates()
    print(f"Found {len(templates.rows)} templates")
    for template in templates.rows[:3]:
        print(f"  - {template['name']} ({template['notetype_name']})")
    
    print("\n2. List cards by deck:")
    cards = anki_list_cards_by_deck("Known Words", 3)
    print(f"Found {len(cards.rows)} cards in Known Words deck")
    
    print("\n3. Get study status:")
    status = anki_get_study_status("Known Words", 3)
    print(f"Found {len(status.rows)} cards with study status")
    for card in status.rows:
        print(f"  - Card {card['id']}: type={card['type']}, reps={card['reps']}")
    
    print("\n4. Test template content:")
    if templates.rows:
        first_template = templates.rows[0]
        content = anki_get_template_content(first_template['name'], first_template['notetype_name'])
        if content:
            print(f"Template {content.name} front HTML: {content.front_html[:100]}...")
        else:
            print("No template content found")

