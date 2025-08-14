"""Pydantic models for Anki data structures."""

from pathlib import Path
from typing import Any

import genanki
from pydantic import BaseModel, Field


class MediaFile(BaseModel):
    """Represents a media file with its filename and binary data."""
    
    filename: str
    data: bytes


class AnkiModel(BaseModel):
    """Represents an Anki note type model."""

    id: int
    name: str
    fields: list[dict[str, Any]]
    templates: list[dict[str, Any]]
    css: str = ""
    original_data: dict[str, Any] = Field(default_factory=dict)

    def to_genanki_model(self) -> genanki.Model:
        """Convert to genanki Model for export."""
        return genanki.Model(
            model_id=self.id,
            name=self.name,
            fields=self.fields,
            templates=self.templates,
            css=self.css,
        )

    def __hash__(self) -> int:
        """Hash based on model ID for deduplication."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on model ID."""
        if not isinstance(other, AnkiModel):
            return False
        return self.id == other.id


class AnkiNote(BaseModel):
    """Represents an Anki note from the database."""

    id: int
    guid: str
    mid: int  # model ID (note type)
    fields: list[str]
    tags: list[str]
    model: AnkiModel | None = None  # Reference to the actual model
    media_files: list[MediaFile] = Field(default_factory=list)  # Media files referenced in this note


class AnkiCard(BaseModel):
    """Represents an Anki card from the database."""

    id: int
    fields: list[str]
    tags: list[str]
    card_type: int
    deck_name: str
    model: AnkiModel | None = None
    note_id: int | None = None  # ID of the source note


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


class AnkiCreateResult(BaseModel):
    """Result of creating Anki cards."""

    deck_path: Path
    cards_created: int
    message: str = ""


class ExampleSentenceResponse(BaseModel):
    """Response model for generated example sentences."""

    source_sentence: str
    target_sentence: str
