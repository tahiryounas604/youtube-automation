import pytest

from youtube_automation.voiceover import (
    generate_voiceover,
    piper_available,
    wav_duration_seconds,
)
from youtube_automation.script_builder import estimate_duration_seconds


def test_silent_track_matches_narration_duration(tmp_path):
    text = " ".join(["word"] * 150)  # 150 words -> 60s at 150 wpm
    out = tmp_path / "voice.wav"
    result = generate_voiceover(text, str(out))
    assert result["engine"] == "silent"
    assert "Piper" in result["note"]
    assert result["duration_seconds"] == pytest.approx(60.0, abs=0.5)
    assert wav_duration_seconds(str(out)) == pytest.approx(60.0, abs=0.5)


def test_silent_track_short_text(tmp_path):
    text = "Hello world, this is a short test."
    out = tmp_path / "voice.wav"
    result = generate_voiceover(text, str(out))
    expected = estimate_duration_seconds(text)
    assert result["duration_seconds"] == pytest.approx(expected, abs=0.5)


def test_generate_voiceover_rejects_empty_text(tmp_path):
    with pytest.raises(ValueError):
        generate_voiceover("   ", str(tmp_path / "x.wav"))


def test_piper_detection_returns_bool():
    # Piper is not installed in this environment; the function must still
    # report honestly either way.
    assert isinstance(piper_available(), bool)
