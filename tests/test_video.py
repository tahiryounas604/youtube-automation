import pytest
from PIL import Image

from youtube_automation.video import (
    assemble_video,
    make_slide_image,
    probe_video,
)


def test_make_slide_image_is_720p(tmp_path):
    out = tmp_path / "slide.png"
    make_slide_image("What DNS Is", str(out), body="How DNS Works")
    img = Image.open(out)
    assert img.size == (1280, 720)


def test_assemble_two_second_clip(tmp_path):
    """Spec test: a 2-second 720p clip from one slide, no audio."""
    slide = tmp_path / "slide.png"
    make_slide_image("Test Slide", str(slide))
    out = tmp_path / "clip.mp4"
    result = assemble_video([str(slide)], str(out), slide_duration=2.0)
    assert result["width"] == 1280
    assert result["height"] == 720
    assert result["duration_seconds"] == pytest.approx(2.0, abs=0.4)
    assert out.stat().st_size > 10_000
    assert probe_video(str(out))["width"] == 1280


def test_assemble_with_audio_and_captions(tmp_path):
    from youtube_automation.voiceover import generate_voiceover

    text = " ".join(["word"] * 75)  # 30s at 150 wpm -> too long; use short text
    text = "Hello world. This is a caption test."
    voice = tmp_path / "voice.wav"
    generate_voiceover(text, str(voice))
    slides = []
    for i in range(2):
        slide = tmp_path / f"slide{i}.png"
        make_slide_image(f"Slide {i + 1}", str(slide))
        slides.append(str(slide))
    captions = [
        {"start": 0.0, "end": 1.0, "text": "Hello world."},
        {"start": 1.0, "end": 2.0, "text": "This is a caption test."},
    ]
    out = tmp_path / "captioned.mp4"
    result = assemble_video(slides, str(out), audio_path=str(voice), captions=captions)
    assert result["width"] == 1280
    assert result["height"] == 720
    # Video length follows the audio track (~2.8s for the test text).
    assert result["duration_seconds"] == pytest.approx(2.8, abs=0.6)


def test_assemble_rejects_missing_slide(tmp_path):
    with pytest.raises(FileNotFoundError):
        assemble_video([str(tmp_path / "nope.png")], str(tmp_path / "x.mp4"))


def test_assemble_rejects_empty_slides(tmp_path):
    with pytest.raises(ValueError):
        assemble_video([], str(tmp_path / "x.mp4"))
