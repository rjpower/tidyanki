"""Test APKG model and media preservation functionality."""

import tempfile
from pathlib import Path

from tidyanki.core.export import export_notes_to_deck
from tidyanki.core.import_apkg import (
    load_media_from_apkg,
    load_models_from_apkg,
    load_notes_from_apkg,
)
from tidyanki.models.anki_models import AnkiNote


def test_apkg_model_preservation():
    """Test that models are preserved when importing and exporting APKG files."""
    # Use the test data file
    apkg_path = Path("tests/testdata/seinfeld.apkg")
    assert apkg_path.exists(), f"Test file not found: {apkg_path}"

    # Load original data
    original_notes = load_notes_from_apkg(apkg_path)
    original_models = load_models_from_apkg(apkg_path)
    original_media = load_media_from_apkg(apkg_path)

    print("Original file has:")
    print(f"  Notes: {original_notes.count()}")
    print(f"  Models: {len(original_models)}")
    print(f"  Media files: {len(original_media)}")

    # Verify we have data to work with
    assert original_notes.count() > 0, "Should have notes"
    assert len(original_models) > 0, "Should have models"

    # Verify notes have model references
    note_list: list[AnkiNote] = original_notes.to_list()
    for note in note_list:
        assert note.model is not None, f"Note {note.id} should have model reference"
        print(f"  Note {note.id} uses model: {note.model.name}")

    # Test export with preservation
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Export all notes (no filtering)
        output_path = temp_path / "exported_seinfeld.apkg"
        result = export_notes_to_deck(
            notes=original_notes,
            deck_name="Exported Seinfeld",
            output_path=output_path,
        )

        print(f"\nExported to: {result.deck_path}")
        print(f"Cards exported: {result.cards_created}")
        print(result.message)

        # Verify export file exists
        assert output_path.exists(), "Export file should exist"

        # Re-import the exported file to verify preservation
        reimported_notes = load_notes_from_apkg(output_path)
        reimported_models = load_models_from_apkg(output_path)
        reimported_media = load_media_from_apkg(output_path)

        print("\nRe-imported file has:")
        print(f"  Notes: {reimported_notes.count()}")
        print(f"  Models: {len(reimported_models)}")
        print(f"  Media files: {len(reimported_media)}")

        # Verify preservation
        assert reimported_notes.count() == original_notes.count(), "Note count should match"
        assert len(reimported_models) == len(original_models), "Model count should match"

        # Verify model details are preserved
        for model_id, original_model in original_models.items():
            assert model_id in reimported_models, f"Model {model_id} should be preserved"
            reimported_model = reimported_models[model_id]

            assert reimported_model.name == original_model.name, "Model name should match"
            assert len(reimported_model.fields) == len(original_model.fields), (
                "Field count should match"
            )
            assert len(reimported_model.templates) == len(original_model.templates), (
                "Template count should match"
            )

            print(f"  ✓ Model {model_id} ({original_model.name}) preserved correctly")

        # Verify notes have correct model references AND content
        reimported_note_list = reimported_notes.to_list()
        for i, (orig_note, reimp_note) in enumerate(
            zip(note_list, reimported_note_list, strict=False)
        ):
            assert orig_note.model is not None, "Original note should have model reference"
            assert reimp_note.model is not None, "Reimported note should have model reference"
            assert reimp_note.model.name == orig_note.model.name, "Model names should match"

            # Validate actual field content is preserved
            assert len(reimp_note.fields) == len(orig_note.fields), (
                f"Note {i + 1} field count should match"
            )
            for j, (orig_field, reimp_field) in enumerate(
                zip(orig_note.fields, reimp_note.fields, strict=False)
            ):
                assert orig_field == reimp_field, (
                    f"Note {i + 1} field {j} content should match: '{orig_field}' vs '{reimp_field}'"
                )

            # Validate tags are preserved
            assert set(reimp_note.tags) == set(orig_note.tags), f"Note {i + 1} tags should match"

            print(f"  ✓ Note {i + 1} content and model preserved: {reimp_note.model.name}")

        # Deep validation: Check that model templates are identical
        for model_id, original_model in original_models.items():
            reimported_model = reimported_models[model_id]

            # Validate field definitions are identical
            assert len(original_model.fields) == len(reimported_model.fields), (
                "Field definitions count should match"
            )
            for orig_field, reimp_field in zip(
                original_model.fields, reimported_model.fields, strict=False
            ):
                orig_name: str = orig_field["name"]
                reimp_name: str = reimp_field["name"]
                assert orig_name == reimp_name
                assert orig_field["ord"] == reimp_field["ord"], "Field order should match"

            # Validate template definitions are identical
            assert len(original_model.templates) == len(reimported_model.templates), (
                "Template count should match"
            )
            for orig_tmpl, reimp_tmpl in zip(
                original_model.templates, reimported_model.templates, strict=False
            ):
                assert orig_tmpl["name"] == reimp_tmpl["name"], "Template name should match"
                assert orig_tmpl["qfmt"] == reimp_tmpl["qfmt"], "Question format should match"
                assert orig_tmpl["afmt"] == reimp_tmpl["afmt"], "Answer format should match"

            # Validate CSS is preserved
            assert original_model.css == reimported_model.css, "CSS should be preserved exactly"

            print(f"  ✓ Model {model_id} template structure preserved identically")

        # If there were media files, verify they're preserved
        if original_media:
            assert len(reimported_media) == len(original_media), "Media count should match"
            print(f"  ✓ Media files preserved: {len(reimported_media)}")

    print("\n✅ All round-trip tests passed! Complete content preservation verified.")


def test_filtering_preserves_models():
    """Test that filtering still preserves original models."""
    apkg_path = Path("tests/testdata/seinfeld.apkg")
    assert apkg_path.exists(), f"Test file not found: {apkg_path}"

    # Load original data
    original_notes = load_notes_from_apkg(apkg_path)
    original_models = load_models_from_apkg(apkg_path)

    # Filter to just first 10 notes
    filtered_notes = original_notes.take(10)

    print("\nFiltering test:")
    print(f"  Original notes: {original_notes.count()}")
    print(f"  Filtered notes: {filtered_notes.count()}")

    # Export filtered set
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "filtered_seinfeld.apkg"
        result = export_notes_to_deck(
            notes=filtered_notes,
            deck_name="Filtered Seinfeld",
            output_path=output_path,
        )

        print(f"  Exported cards: {result.cards_created}")

        # Verify filtered export
        reimported_notes = load_notes_from_apkg(output_path)
        reimported_models = load_models_from_apkg(output_path)

        assert reimported_notes.count() == 10, "Should have 10 filtered notes"
        assert len(reimported_models) > 0, "Should still have models"

        # Verify models are still correct
        reimported_note_list = reimported_notes.to_list()
        for note in reimported_note_list:
            assert note.model is not None, "Filtered note should have model reference"
            assert note.model.name in [m.name for m in original_models.values()], (
                "Should use original model"
            )

    print("  ✅ Filtering preserves models correctly")


if __name__ == "__main__":
    test_apkg_model_preservation()
    test_filtering_preserves_models()