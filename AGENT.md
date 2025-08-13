# TidyAnki Agent Instructions

## Project Overview

**TidyAnki** is a Python library and CLI tool for manipulating Anki collections and decks. It provides utilities for analyzing, deduplicating, searching, and exporting Anki card data programmatically.

**Main Goals:**
- Analyze and manipulate Anki deck/card data
- Remove duplicate cards from decks
- Export filtered/deduplicated decks
- Search and compare decks
- Provide both programmatic API and CLI interface

## Repository Structure

```
tidyanki/
├── src/tidyanki/           # Main package
│   ├── __init__.py         # Package exports
│   ├── tidyanki.py         # CLI interface 
│   ├── core/               # Core functionality
│   │   ├── anki_db.py      # Database connection utilities
│   │   ├── tables.py       # Data table abstractions
│   │   ├── operations.py   # Card/template operations
│   │   ├── deduplication.py # Duplicate detection/removal
│   │   └── export.py       # Deck export functionality
│   └── models/             # Data models
│       └── anki_models.py  # Pydantic models for Anki data
├── tests/                  # Test files
├── devtools/               # Development utilities
│   └── lint.py            # Linting script
├── pyproject.toml         # Project configuration
└── Makefile              # Development commands
```

## Key Components

### Core Tables (`src/tidyanki/core/tables.py`)
- `AnkiDecksTable` - Loads and queries deck information
- `AnkiCardsTable` - Loads and queries card data 
- `AnkiCardsWithStatusTable` - Cards with review status

### Operations (`src/tidyanki/core/operations.py`)
- Template management (`get_templates`, `get_template_content`)
- Card creation (`create_vocab_cards`)
- Example sentence generation

### Deduplication (`src/tidyanki/core/deduplication.py`)
- `find_duplicate_cards` - Detect duplicates within deck
- `remove_duplicate_cards` - Remove duplicates
- `analyze_deck_overlap` - Compare cards between decks

### Export (`src/tidyanki/core/export.py`)
- `export_cards_to_deck` - Export cards to .apkg file
- `export_deduplicated_deck` - Export with duplicates removed
- `export_filtered_deck` - Export subset of cards

## Available Commands

### Development Commands (Makefile)
```bash
make install    # Install dependencies with uv sync
make lint       # Run linting (ruff + pyrefly)
make test       # Run pytest
make build      # Build package
make clean      # Clean build artifacts
```

### CLI Commands (via `tidyanki` script)
```bash
tidyanki decks                           # List all decks
tidyanki cards <deck> [--limit N]        # List cards in deck
tidyanki search <query> [--deck <name>]  # Search cards
tidyanki deduplicate <deck> [--output]   # Remove duplicates
tidyanki compare <deck1> <deck2>         # Compare deck overlap
tidyanki templates                       # List card templates
```

## Dependencies

**Core:**
- `pydantic` - Data validation/models
- `tidylinq` - Data querying
- `genanki` - Anki package generation
- `unidecode` - Text normalization

**Development:**
- `pytest` - Testing
- `ruff` - Linting/formatting
- `funlog` - Logging utilities
- `rich` - Terminal output
- `litellm` - AI integration

## Development Workflow

1. **Setup**: `make install` to sync dependencies
2. **Coding**: Follow Python 3.11+ standards with full type hints
3. **Linting**: `make lint` runs ruff formatting and pyrefly type checking
4. **Testing**: `make test` runs pytest
5. **Complete**: `make` runs install + lint + test

## Entry Points

- **CLI**: `tidyanki` command (via `pyproject.toml` scripts)
- **API**: Import from `tidyanki` package for programmatic use
- **Main**: `tidyanki.main()` function for CLI interface


## Style

* Always use absolute imports (from package import x), not relative (from .y import x)