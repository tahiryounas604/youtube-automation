import pytest

from youtube_automation.script_builder import (
    build_captions,
    build_script,
    estimate_duration_seconds,
    load_outline,
    split_sentences,
)

SECTIONS = [
    {"heading": "What DNS Is", "points": ["DNS is the phonebook of the internet",
                                          "it turns domain names into IP addresses"]},
    {"heading": "Caching", "points": ["answers are cached to keep things fast"]},
]


def test_build_script_contains_topic_headings_and_points():
    script = build_script("How DNS Works", SECTIONS)
    assert script["topic"] == "How DNS Works"
    assert "How DNS Works" in script["narration"]
    for section in SECTIONS:
        assert section["heading"] in script["narration"]
        for point in section["points"]:
            assert point in script["narration"]
    assert script["word_count"] == len(script["narration"].split())
    assert script["word_count"] > 30
    assert script["estimated_duration_seconds"] > 0
    assert len(script["sections"]) == 2


def test_build_script_styles_change_intro():
    edu = build_script("How DNS Works", SECTIONS, style="educational")
    lst = build_script("How DNS Works", SECTIONS, style="listicle")
    assert "Number 1:" in lst["narration"]
    assert "Number 1:" not in edu["narration"]


def test_build_script_rejects_bad_input():
    with pytest.raises(ValueError):
        build_script("", SECTIONS)
    with pytest.raises(ValueError):
        build_script("Topic", [])
    with pytest.raises(ValueError):
        build_script("Topic", [{"heading": "Only heading"}])
    with pytest.raises(ValueError):
        build_script("Topic", SECTIONS, style="nope")


def test_estimate_duration_scales_with_words():
    short = estimate_duration_seconds("one two three four five six")
    long = estimate_duration_seconds(" ".join(["word"] * 300))
    assert long > short
    assert estimate_duration_seconds(" ".join(["word"] * 150)) == pytest.approx(60.0)


def test_split_sentences_keeps_punctuation():
    assert split_sentences("Hello world. How are you? Fine!") == [
        "Hello world.", "How are you?", "Fine!",
    ]


def test_build_captions_cover_full_narration_and_time_order():
    script = build_script("How DNS Works", SECTIONS)
    captions = build_captions(script["narration"])
    assert captions
    assert captions[0]["start"] == 0
    joined = " ".join(c["text"] for c in captions)
    assert joined.split() == script["narration"].split()
    for prev, cur in zip(captions, captions[1:]):
        assert cur["start"] >= prev["end"] - 0.01
        assert cur["end"] > cur["start"]
    # Last caption ends at the estimated narration duration.
    assert captions[-1]["end"] == pytest.approx(
        script["estimated_duration_seconds"], abs=0.1
    )


def test_load_outline_round_trip(tmp_path):
    outline = {"topic": "How DNS Works", "style": "educational", "sections": SECTIONS}
    import json

    path = tmp_path / "outline.json"
    path.write_text(json.dumps(outline), encoding="utf-8")
    assert load_outline(str(path)) == outline
