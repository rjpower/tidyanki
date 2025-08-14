"""Test media extraction from card fields."""

from tidyanki.core.import_apkg import detect_media_in_fields


def test_audio_detection():
    """Test detection of audio files in [sound:filename] format."""
    fields = [
        'その子は大粒の涙を浮かべていたの。',
        "The child's eyes were brimming with big tears.<br />粒 -- grain, drop",
        'その こ は おおつぶ の なみだ を うかべていた の',
        '[sound:a8243f998a6ba4f0c5d57f6eaeb2d66c.mp3]',
        '',
        'sentence:304524',
        'sentence'
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['a8243f998a6ba4f0c5d57f6eaeb2d66c.mp3']
    
    assert result == expected


def test_image_detection():
    """Test detection of image files in <img src="filename"> format."""
    fields = [
        'English text',
        '<img src="image123.jpg">',
        'More text',
        'Other field'
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['image123.jpg']
    
    assert result == expected


def test_mixed_media():
    """Test detection of both image and audio files."""
    fields = [
        'Text with <img src="photo.png">',
        '[sound:audio.mp3]',
        'Plain text'
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['photo.png', 'audio.mp3']
    
    assert set(result) == set(expected)


def test_no_media():
    """Test fields with no media references."""
    fields = [
        'Plain text',
        'No media here',
        'Just words'
    ]
    
    result = detect_media_in_fields(fields)
    expected = []
    
    assert result == expected


def test_multiple_media_in_single_field():
    """Test multiple media references in a single field."""
    fields = [
        'Text <img src="pic1.jpg"> more text [sound:file.mp3] end'
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['pic1.jpg', 'file.mp3']
    
    assert set(result) == set(expected)


def test_case_insensitive():
    """Test that media detection is case insensitive."""
    fields = [
        'Text with <IMG SRC="photo.PNG">',
        '[SOUND:audio.MP3]',
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['photo.PNG', 'audio.MP3']
    
    assert set(result) == set(expected)


def test_various_image_formats():
    """Test detection of various image file formats."""
    fields = [
        '<img src="image.jpg">',
        '<img src="photo.png">',
        '<img src="graphic.gif">',
        '<img src="vector.svg">',
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['image.jpg', 'photo.png', 'graphic.gif', 'vector.svg']
    
    assert set(result) == set(expected)


def test_various_audio_formats():
    """Test detection of various audio file formats."""
    fields = [
        '[sound:audio.mp3]',
        '[sound:voice.wav]',
        '[sound:music.ogg]',
        '[sound:sound.m4a]',
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['audio.mp3', 'voice.wav', 'music.ogg', 'sound.m4a']
    
    assert set(result) == set(expected)


def test_duplicate_removal():
    """Test that duplicate media references are removed."""
    fields = [
        '<img src="same.jpg">',
        '[sound:same.mp3]',
        '<img src="same.jpg">',  # Duplicate
        '[sound:same.mp3]',      # Duplicate
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['same.jpg', 'same.mp3']
    
    assert set(result) == set(expected)
    assert len(result) == 2  # No duplicates


def test_complex_html_with_media():
    """Test media detection in complex HTML content."""
    fields = [
        '<div><img src="complex.jpg" alt="test" class="image"></div>',
        '<p>Text before <img src="inline.png" /> text after</p>',
        'Audio: [sound:complex_audio.mp3] with text',
    ]
    
    result = detect_media_in_fields(fields)
    expected = ['complex.jpg', 'inline.png', 'complex_audio.mp3']
    
    assert set(result) == set(expected)