import hashlib
import json
import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from tidyanki.config.languages import Language
from tidyanki.models.vocabulary import VocabItem

ProgressLogger = Callable[[str], None]


class VocabItems(BaseModel):
    items: list[VocabItem]


def _get_cache_path(messages: list[dict], cache_dir: Path) -> Path:
    """Generate cache file path from messages"""
    cache_key = json.dumps({"messages": messages}, sort_keys=True)
    hash_key = hashlib.md5(cache_key.encode()).hexdigest()
    return cache_dir / f"{hash_key}.json"


def cached_completion(
    messages: list[dict],
    response_format: type[BaseModel] | dict[str, str] | None = None,
    cache_dir: Path | None = None,
    model: str = "gemini/gemini-2.0-flash-exp",
) -> str:
    """Execute LLM completion with caching

    Args:
        messages: The messages to send to the LLM
        response_format: Optional Pydantic model for structured output
        cache_dir: Directory to store cache files
        model: Model ID to use for completion

    Returns:
        Response content from LLM
    """
    import litellm

    if cache_dir is None:
        cache_dir = Path.home() / ".tidyanki" / "cache"

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = _get_cache_path(messages, cache_dir)
    if cache_path.exists():
        logging.debug("Cache hit for completion")
        return cache_path.read_text(encoding="utf-8")

    logging.debug("Cache miss, calling LLM")
    response = litellm.completion(  # type: ignore[misc]
        model=model,
        messages=messages,
        response_format=response_format,
    )

    result = response.choices[0].message.content
    cache_path.write_text(result)
    return result


def infer_field_mapping(
    df: pd.DataFrame, source_language: Language, target_language: Language
) -> dict:
    """Get LLM suggestions for CSV field mapping using column letters"""
    logging.debug("Inferring field mapping for CSV data")
    preview_rows = df.head(25).fillna("").astype(str).values.tolist()
    sample_data = "\n".join([",".join(df.columns), *[",".join(row) for row in preview_rows]])

    prompt = f"""Analyze this CSV data and suggest mappings for a vocabulary flashcard system.
The system has the following fields:

* term: the {source_language.name} word or phrase
* reading: the pronunciation of the term, e.g. Hiragana or Katakana for Japanese, Pinyin for Chinese, etc.
* meaning: the {target_language.name} translation of the term
* context_native: a {source_language.name} sentence using the term
* context_en: the {target_language.name} translation of the sentence

One of "term" or "meaning" is mandatory. "term" must be a {source_language.name} word or phrase.  "meaning" must be a {target_language.name} word or phrase.
If you don't have a value for a field, leave it blank.

The columns are labeled with letters (A, B, C, etc.).
Look at the content in each column to suggest the best mapping.

CSV Data (first few rows):
{sample_data}


Return only valid JSON in this format:
{{
    "suggested_mapping": {{
        "term": "A",
        "reading": "B",
        "meaning": "C",
        "context_native": "D" or null,
        "context_en": "E" or null,
    }},
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of why each column was mapped based on its content"
}}"""

    return json.loads(
        cached_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    )


def _infer_missing_fields_chunk(
    chunk: Sequence[VocabItem],
    progress_logger: ProgressLogger = logging.info,
) -> list[VocabItem]:
    """Process a chunk of vocabulary items to infer missing fields"""
    complete_records = [
        item
        for item in chunk
        if item.term and item.reading and item.meaning and item.context_native and item.context_en
    ]
    incomplete_records = [item for item in chunk if item not in complete_records]

    if not incomplete_records:
        return complete_records

    progress_logger(f"Inferring missing fields for {len(incomplete_records)} incomplete records")

    items_data = [item.model_dump(exclude_unset=False) for item in incomplete_records]

    prompt = f"""
<instructions>
Given the vocabulary items in the <input> section below, infer any missing fields.
Description of each field:

- term: the original term - this is always provided by the user
- reading: the phonetic reading of the term if relevant -- use Hiragana or Katakana for Japanese, Pinyin for Chinese.
- meaning: meaning of the term in English, if multiple meanings are common, separate with commas
- context_native: a sentence in the native language using the vocabulary from the `term` field.
  This should be a complete sentence that uses the term in context.
  For Chinese and Japanese, use Ruby annotations for word pronunciation in the appropriate format (e.g. Hiragana, Katakana, Pinyin).
- context_en: Translation of the example sentence into English

Output only JSON.
Output a single JSON object with a key "items" containing an array of objects.

{{
  "items": [
    {{
        "term": "図書館",
        "reading": "としょかん",
        "meaning": "library",
        "context_native": "<ruby>図書館<rt>としょかん</rt></ruby>から<ruby>本<rt>ほん</rt></ruby>を<ruby>借<rt>か</rt></ruby>りました。",
        "context_en": "I borrowed a book from the library."
    }},
    {{
        "term": "病院",
        "reading": "びょういん",
        "meaning": "hospital",
        "context_native": "<ruby>病院<rt>びょういん</rt></ruby>に行きました。",
        "context_en": "I went to the hospital."
    }}
  ]
}}
</instructions>

<input>
{json.dumps(items_data, ensure_ascii=False, sort_keys=True)}
</input>
"""

    result = VocabItems.model_validate_json(
        cached_completion(
            messages=[{"role": "user", "content": prompt}], response_format=VocabItems
        )
    )

    return complete_records + result.items


def infer_missing_fields(
    rows: Sequence[VocabItem],
    progress_logger: ProgressLogger = logging.info,
    infer_chunk_size: int = 25,
) -> list[VocabItem]:
    """Process vocabulary items in parallel chunks with progress tracking"""
    # Split into chunks
    chunks = [rows[i : i + infer_chunk_size] for i in range(0, len(rows), infer_chunk_size)]
    total = len(chunks)
    completed = 0
    all_results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_chunk = {
            executor.submit(_infer_missing_fields_chunk, chunk, progress_logger): chunk
            for chunk in chunks
        }

        # Process completed chunks as they finish
        for future in as_completed(future_to_chunk):
            completed += 1
            progress_logger(f"Processed chunk {completed}/{total} ({completed / total * 100:.1f}%)")

            try:
                chunk_results = future.result()
                all_results.extend(chunk_results)
            except Exception as e:
                progress_logger(f"Error processing chunk: {str(e)}")

    return all_results
