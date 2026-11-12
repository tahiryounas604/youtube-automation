import pytest

from youtube_automation.metadata import MAX_TAGS_CHARS, generate_metadata
from youtube_automation.script_builder import build_script

SECTIONS = [
    {"heading": "What DNS Is", "points": ["DNS is the phonebook of the internet"]},
    {"heading": "Caching", "points": ["answers are cached to keep things fast"]},
]


def test_generate_metadata_titles_and_description():
    script = build_script("How DNS Works", SECTIONS)
    meta = generate_metadata("How DNS Works", script, channel_name="Tytechlabs")
    assert len(meta["titles"]) == 3
    assert all(len(t) <= 100 for t in meta["titles"])
    assert all("How DNS Works" in t for t in meta["titles"])
    assert meta["title"] == meta["titles"][0]
    assert "How DNS Works" in meta["description"]
    assert "What DNS Is" in meta["description"]
    assert "Caching" in meta["description"]
    assert "Tytechlabs" in meta["description"]
    assert meta["category_id"] == "27"


def test_generate_metadata_tags_from_topic_and_headings():
    script = build_script("How DNS Works", SECTIONS)
    meta = generate_metadata("How DNS Works", script)
    assert "dns" in meta["tags"]
    assert "caching" in meta["tags"]
    assert len(meta["tags"]) == len(set(meta["tags"]))  # deduplicated
    assert len(meta["tags"]) <= 30
    assert sum(len(t) + 1 for t in meta["tags"]) <= MAX_TAGS_CHARS + 1


def test_generate_metadata_without_script():
    meta = generate_metadata("Solar Panels")
    assert "solar" in meta["tags"]
    assert "Solar Panels" in meta["title"]
    assert meta["description"]


def test_generate_metadata_rejects_empty_topic():
    with pytest.raises(ValueError):
        generate_metadata("   ")
