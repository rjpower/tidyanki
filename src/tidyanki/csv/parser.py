import io
import logging
from pathlib import Path

import pandas as pd

from tidyanki.models.vocabulary import SourceMapping, VocabItem


def read_csv(file_path: Path | str) -> tuple[str, pd.DataFrame]:
    """Read CSV file and auto-detect separator

    Returns:
        Tuple of (separator, DataFrame with column letters as column names)
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    file_content = file_path.read_text(encoding="utf-8")

    separators = [",", "\t", ";"]

    # Find best separator by trying each
    best_separator = ","
    max_columns = 0
    for sep in separators:
        try:
            df = pd.read_csv(io.StringIO(file_content), sep=sep, nrows=1, dtype=str)
            if len(df.columns) > max_columns:
                max_columns = len(df.columns)
                best_separator = sep
        except Exception:
            logging.debug("Failed to read CSV with separator: %s", sep)
            continue

    # Read full file with best separator
    df = pd.read_csv(io.StringIO(file_content), sep=best_separator, dtype=str)
    df = df.fillna("")

    # Generate column letters (A, B, C, etc.)
    num_cols = len(df.columns)
    col_letters = [chr(65 + i) for i in range(num_cols)]  # A=65 in ASCII

    df.columns = col_letters

    return best_separator, df


def load_csv_items(
    df: pd.DataFrame,
    mapping: SourceMapping,
) -> list[VocabItem]:
    """Load vocabulary items from a DataFrame using the specified field mapping

    Args:
        df: Pandas DataFrame containing vocabulary data
        mapping: Field mapping configuration

    Returns:
        List of validated vocabulary items
    """
    logging.debug("Processing DataFrame with %d rows", len(df))
    rows = []
    for _, row in df.iterrows():
        item_data = {
            "term": row.get(mapping.term, "") if mapping.term else "",
            "reading": row.get(mapping.reading, "") if mapping.reading else "",
            "meaning": row.get(mapping.meaning, "") if mapping.meaning else "",
            "context_native": (row.get(mapping.context_native) if mapping.context_native else ""),
            "context_en": row.get(mapping.context_en) if mapping.context_en else "",
            "source": "csv_import",
        }

        # Only add items that have at least one non-empty main field
        if any([item_data["term"], item_data["reading"], item_data["meaning"]]):
            item = VocabItem.model_validate(item_data)
            rows.append(item)
    return rows


def remove_duplicate_terms(vocab_items: list[VocabItem]) -> list[VocabItem]:
    """Remove items with duplicate terms, keeping the first occurrence"""
    seen_terms = set()
    unique_items = []

    for item in vocab_items:
        if item.term not in seen_terms:
            seen_terms.add(item.term)
            unique_items.append(item)

    return unique_items
