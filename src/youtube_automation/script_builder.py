"""Script builder: assemble a narration script from a topic + outline.

No paid AI is involved. The narration is assembled from templates filled
with the caller's own outline, so the creator stays in control of every
word. To plug in an LLM later, replace :func:`build_script`'s template
filling with a call to your model and keep the same return shape
(``{"topic", "title", "narration", "sections", "word_count",
"estimated_duration_seconds"}``) — every downstream step (voiceover,
captions, video assembly) only reads those fields.
"""

from __future__ import annotations

import re

DEFAULT_WPM = 150  # average English narration pace

INTRO_HOOKS = [
    "Here's something most people get wrong about {topic}.",
    "If you've ever wondered about {topic}, this video is for you.",
    "Let's break down {topic} — simply, clearly, and without the fluff.",
]

OUTRO_CTAS = [
    "If this helped, subscribe for more videos like this one.",
    "Like and subscribe if you want part two.",
    "Drop a comment with what you want covered next — and subscribe.",
]


def _ensure_sentence(text: str) -> str:
    """Make sure a fragment ends with sentence punctuation."""
    text = text.strip()
    if not text:
        return text
    if text[-1] not in ".!?":
        text += "."
    return text


def _word_count(text: str) -> int:
    return len(text.split())


def estimate_duration_seconds(text: str, wpm: int = DEFAULT_WPM) -> float:
    """Estimated spoken duration of *text* at *wpm* words per minute."""
    if wpm <= 0:
        raise ValueError("wpm must be positive")
    return round(_word_count(text) / wpm * 60.0, 2)


def split_sentences(text: str) -> list[str]:
    """Split narration into sentences (keeps the punctuation)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def build_script(
    topic: str,
    sections: list[dict],
    style: str = "educational",
    hook_index: int = 0,
    cta_index: int = 0,
) -> dict:
    """Assemble a narration script from *topic* and an outline.

    *sections* is a list of ``{"heading": str, "points": [str, ...]}``.
    Returns a dict with topic, title, narration, per-section narration,
    word count and estimated spoken duration.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    if not sections:
        raise ValueError("sections must contain at least one section")
    for section in sections:
        if not section.get("heading") or not section.get("points"):
            raise ValueError("each section needs a 'heading' and non-empty 'points'")

    hook = INTRO_HOOKS[hook_index % len(INTRO_HOOKS)].format(topic=topic)
    cta = OUTRO_CTAS[cta_index % len(OUTRO_CTAS)]
    style = style.lower()
    if style not in ("educational", "listicle", "story"):
        raise ValueError("style must be 'educational', 'listicle' or 'story'")

    if style == "listicle":
        intro = f"{hook} Today we count down {len(sections)} key points about {topic}."
    elif style == "story":
        intro = f"{hook} This is the story of {topic} — and it starts with a simple question."
    else:
        intro = f"{hook} In this video, we'll cover {len(sections)} parts of {topic}, step by step."

    headings = [s["heading"] for s in sections]
    intro += " Here's what we'll cover: " + "; ".join(headings) + "."

    section_texts: list[dict] = []
    body_parts: list[str] = []
    for i, section in enumerate(sections, start=1):
        points = [_ensure_sentence(p) for p in section["points"]]
        if style == "listicle":
            lead = f"Number {i}: {section['heading']}."
        else:
            lead = f"{section['heading']}."
        text = lead + " " + " ".join(points)
        section_texts.append(
            {"heading": section["heading"], "narration": text, "word_count": _word_count(text)}
        )
        body_parts.append(text)

    recap = "To recap: " + "; ".join(headings) + "."
    outro = f"{recap} {cta}"

    narration = intro + "\n\n" + "\n\n".join(body_parts) + "\n\n" + outro
    return {
        "topic": topic,
        "title": topic,
        "style": style,
        "narration": narration,
        "sections": section_texts,
        "word_count": _word_count(narration),
        "estimated_duration_seconds": estimate_duration_seconds(narration),
    }


def build_captions(narration: str, wpm: int = DEFAULT_WPM, max_words: int = 8) -> list[dict]:
    """Split *narration* into timed caption chunks.

    Each caption holds at most *max_words* words and is timed at *wpm*.
    Returns a list of ``{"start", "end", "text"}`` dicts with times in
    seconds — the same shape :mod:`youtube_automation.video` consumes
    for burned-in drawtext captions.
    """
    if wpm <= 0:
        raise ValueError("wpm must be positive")
    seconds_per_word = 60.0 / wpm
    captions: list[dict] = []
    t = 0.0
    for sentence in split_sentences(narration):
        words = sentence.split()
        for i in range(0, len(words), max_words):
            chunk = words[i : i + max_words]
            duration = round(len(chunk) * seconds_per_word, 2)
            captions.append(
                {"start": round(t, 2), "end": round(t + duration, 2), "text": " ".join(chunk)}
            )
            t += duration
    return captions


def load_outline(path: str) -> dict:
    """Load a topic outline from a JSON file.

    Expected shape: ``{"topic": str, "style": str?, "sections":
    [{"heading": str, "points": [str, ...]}]}``.
    """
    import json

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "topic" not in data or "sections" not in data:
        raise ValueError("outline JSON must contain 'topic' and 'sections'")
    return data
