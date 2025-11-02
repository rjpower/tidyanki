from pydantic import BaseModel


class VocabItem(BaseModel):
    term: str
    reading: str = ""
    meaning: str = ""
    context_native: str = ""
    context_en: str = ""
    source: str = ""

    @property
    def front(self) -> str:
        return self.term

    @property
    def front_sub(self) -> str | None:
        return self.reading

    @property
    def front_context(self) -> str | None:
        return self.context_native

    @property
    def back(self) -> str:
        return self.meaning or ""

    @property
    def back_context(self) -> str | None:
        return self.context_en


class SourceMapping(BaseModel):
    """Maps source document fields to VocabItem fields"""

    term: str
    reading: str | None = None
    meaning: str | None = None
    context_native: str | None = None
    context_en: str | None = None
