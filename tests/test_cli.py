import json
import os

from PIL import Image

from youtube_automation.cli import main
from youtube_automation.video import probe_video

TINY_OUTLINE = {
    "topic": "Test Topic",
    "style": "educational",
    "sections": [{"heading": "One Idea", "points": ["Short point."]}],
}


def test_cli_script_and_meta(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outline = tmp_path / "outline.json"
    outline.write_text(json.dumps(TINY_OUTLINE), encoding="utf-8")
    assert main(["script", str(outline), "-o", "script.json"]) == 0
    script = json.loads((tmp_path / "script.json").read_text())
    assert script["topic"] == "Test Topic"
    assert main(["meta", "Test Topic", "--script", "script.json",
                 "-o", "meta.json"]) == 0
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["title"]
    assert main(["thumb", "Test Topic", "-o", "thumb.png"]) == 0
    assert Image.open(tmp_path / "thumb.png").size == (1280, 720)


def test_cli_pipeline_end_to_end(tmp_path, monkeypatch):
    """Full pipeline: outline -> script -> voice -> slides -> video -> thumb -> meta."""
    monkeypatch.chdir(tmp_path)
    outline = tmp_path / "outline.json"
    outline.write_text(json.dumps(TINY_OUTLINE), encoding="utf-8")
    assert main(["pipeline", str(outline), "-o", "out",
                 "--schedule", "2026-11-13T10:00:00Z"]) == 0
    out = tmp_path / "out"
    for name in ("script.json", "voiceover.wav", "captions.json",
                 "slide_1.png", "video.mp4", "thumbnail.png", "metadata.json"):
        assert (out / name).exists(), f"missing pipeline output: {name}"
    info = probe_video(str(out / "video.mp4"))
    assert (info["width"], info["height"]) == (1280, 720)
    assert info["duration_seconds"] > 0
    queue = json.loads((tmp_path / "queue.json").read_text())
    assert len(queue) == 1 and queue[0]["topic"] == "Test Topic"


def test_cli_bad_outline_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"topic": "No sections"}), encoding="utf-8")
    assert main(["script", str(bad), "-o", "s.json"]) == 1
