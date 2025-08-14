"""Test APKG model and media preservation functionality."""

import tempfile
from pathlib import Path

from tidyanki.core.export import export_cards_to_deck
from tidyanki.core.import_apkg import (
    extract_media_files,
    load_cards_from_apkg,
    load_media_from_apkg,
    load_notes_from_apkg,
)
from tidyanki.models.anki_models import AnkiCard


def test_apkg_model_preservation():
    """Test that models are preserved when importing and exporting APKG files."""
    # Use the test data file
    apkg_path = Path("tests/testdata/seinfeld.apkg")
    assert apkg_path.exists(), f"Test file not found: {apkg_path}"

    # Load original data
    original_notes = load_notes_from_apkg(apkg_path)
    original_cards, original_models = load_cards_from_apkg(apkg_path)
    original_media = load_media_from_apkg(apkg_path)

    print("Original file has:")
    print(f"  Notes: {original_notes.count()}")
    print(f"  Cards: {original_cards.count()}")
    print(f"  Models: {len(original_models)}")
    print(f"  Media files: {len(original_media)}")

    # Verify we have data to work with
    assert original_notes.count() > 0, "Should have notes"
    assert original_cards.count() > 0, "Should have cards"
    assert len(original_models) > 0, "Should have models"

    # Verify cards have model references
    card_list: list[AnkiCard] = original_cards.to_list()
    for card in card_list:
        assert card.model is not None, f"Card {card.id} should have model reference"
        print(f"  Card {card.id} uses model: {card.model.name}")

    # Test export with preservation
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Extract media files if any
        extracted_media = []
        if original_media:
            extracted_media = extract_media_files(apkg_path, temp_path)

        # Export all cards (no filtering)
        output_path = temp_path / "exported_seinfeld.apkg"
        result = export_cards_to_deck(
            cards=original_cards,
            deck_name="Exported Seinfeld",
            output_path=output_path,
            media_files=[str(f) for f in extracted_media] if extracted_media else None,
        )

        print(f"\nExported to: {result.deck_path}")
        print(f"Cards exported: {result.cards_created}")
        print(result.message)

        # Verify export file exists
        assert output_path.exists(), "Export file should exist"
        assert result.cards_created == original_cards.count(), "Should export all cards"

        # Re-import the exported file to verify preservation
        reimported_notes = load_notes_from_apkg(output_path)
        reimported_cards, reimported_models = load_cards_from_apkg(output_path)
        reimported_media = load_media_from_apkg(output_path)

        print("\nRe-imported file has:")
        print(f"  Notes: {reimported_notes.count()}")
        print(f"  Cards: {reimported_cards.count()}")
        print(f"  Models: {len(reimported_models)}")
        print(f"  Media files: {len(reimported_media)}")

        # Verify preservation
        assert reimported_cards.count() == original_cards.count(), "Card count should match"
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

        # Verify cards have correct model references AND content
        reimported_card_list = reimported_cards.to_list()
        for i, (orig_card, reimp_card) in enumerate(
            zip(card_list, reimported_card_list, strict=False)
        ):
            assert orig_card.model is not None, "Original card should have model reference"
            assert reimp_card.model is not None, "Reimported card should have model reference"
            assert reimp_card.model.name == orig_card.model.name, "Model names should match"

            # Validate actual field content is preserved
            assert len(reimp_card.fields) == len(orig_card.fields), (
                f"Card {i + 1} field count should match"
            )
            for j, (orig_field, reimp_field) in enumerate(
                zip(orig_card.fields, reimp_card.fields, strict=False)
            ):
                assert orig_field == reimp_field, (
                    f"Card {i + 1} field {j} content should match: '{orig_field}' vs '{reimp_field}'"
                )

            # Validate tags are preserved
            assert set(reimp_card.tags) == set(orig_card.tags), f"Card {i + 1} tags should match"

            print(f"  ✓ Card {i + 1} content and model preserved: {reimp_card.model.name}")

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
    original_cards, original_models = load_cards_from_apkg(apkg_path)

    # Filter to just first 10 cards
    filtered_cards = original_cards.take(10)

    print("\nFiltering test:")
    print(f"  Original cards: {original_cards.count()}")
    print(f"  Filtered cards: {filtered_cards.count()}")

    # Export filtered set
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "filtered_seinfeld.apkg"
        result = export_cards_to_deck(
            cards=filtered_cards,
            deck_name="Filtered Seinfeld",
            output_path=output_path,
        )

        print(f"  Exported cards: {result.cards_created}")

        # Verify filtered export
        reimported_cards, reimported_models = load_cards_from_apkg(output_path)

        assert reimported_cards.count() == 10, "Should have 10 filtered cards"
        assert len(reimported_models) > 0, "Should still have models"

        # Verify models are still correct
        reimported_card_list = reimported_cards.to_list()
        for card in reimported_card_list:
            assert card.model is not None, "Filtered card should have model reference"
            assert card.model.name in [m.name for m in original_models.values()], (
                "Should use original model"
            )

    print("  ✅ Filtering preserves models correctly")


if __name__ == "__main__":
    test_apkg_model_preservation()
    test_filtering_preserves_models()
