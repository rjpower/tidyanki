"""Field extraction functionality."""

import csv
from io import StringIO

from tidylinq import Table

from tidyanki.models.anki_models import AnkiNote


def extract_fields_from_notes(notes: Table[AnkiNote], field_indices: list[int]) -> str:
    """Extract specified fields from notes as CSV.

    Args:
        notes: Table of notes to extract fields from
        field_indices: List of field indices to extract

    Returns:
        CSV string with note_id and requested fields
    """
    output = StringIO()
    writer = csv.writer(output)

    headers = ["note_id"] + [f"field_{i}" for i in field_indices]
    writer.writerow(headers)

    for note in notes:
        row = [str(note.id)]
        for field_index in field_indices:
            if len(note.fields) > field_index:
                row.append(note.fields[field_index])
            else:
                row.append("")
        writer.writerow(row)

    return output.getvalue()
