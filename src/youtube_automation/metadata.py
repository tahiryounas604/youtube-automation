"""Metadata / SEO generator: titles, description and tags.

Pure text generation from the topic and the script — no network, no
API keys. Titles are kept within YouTube's 100-character limit and
tags within the 500-character total limit.
"""

from __future__ import annotations

import re

MAX_TITLE_CHARS = 100
MAX_TAGS_CHARS = 500
MAX_TAGS = 30

GENERIC_TAGS = ["how to", "explained", "tutorial", "beginners guide", "learn"]


def _keywords(topic: str, script: dict | None) -> list[str]:
    """Keywords from the topic and section headings, deduplicated."""
    words: list[str] = []
    seen: set[str] = set()
    sources = [topic]
    if script:
        sources += [s["heading"] for s in script.get("sections", [])]
    stop = {"and", "the", "for", "with", "how", "what", "why", "your", "you"}
    for source in sources:
        for token in re.split(r"[^A-Za-z0-9]+", source.lower()):
            token = token.strip()
            if len(token) > 2 and token not in stop and token not in seen:
                seen.add(token)
                words.append(token)
    return words


def generate_metadata(
    topic: str,
    script: dict | None = None,
    channel_name: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict:
    """Generate YouTube metadata for *topic*.

    Returns ``{"titles", "title", "description", "tags",
    "category_id"}``. ``titles`` holds three variants (best first);
    ``title`` is the recommended one.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    keywords = _keywords(topic, script)

    titles = [
        f"{topic} Explained Simply",
        f"{topic}: Everything You Need to Know",
        f"How {topic} Works — A Beginner's Guide",
    ]
    titles = [t[:MAX_TITLE_CHARS] for t in titles]

    headings = [s["heading"] for s in (script or {}).get("sections", [])]
    lines = [f"{topic} — explained simply, step by step.", ""]
    if headings:
        lines.append("In this video:")
        lines += [f"• {h}" for h in headings]
        lines.append("")
    lines.append(
        "If this helped, like the video and subscribe for more clear, "
        "no-fluff explainers."
    )
    if channel_name:
        lines += ["", f"More from {channel_name} — new videos every week."]
    tags = keywords + [t for t in GENERIC_TAGS if t not in keywords]
    for extra in extra_tags or []:
        if extra.strip() and extra.strip().lower() not in tags:
            tags.append(extra.strip().lower())
    tags = tags[:MAX_TAGS]
    # Enforce YouTube's 500-character total tag limit.
    total = 0
    kept: list[str] = []
    for tag in tags:
        if total + len(tag) + (1 if kept else 0) > MAX_TAGS_CHARS:
            break
        kept.append(tag)
        total += len(tag) + 1
    tags = kept

    hashtags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", k) for k in keywords[:3])
    description = "\n".join(lines)
    if hashtags.strip("# "):
        description += "\n\n" + hashtags

    return {
        "titles": titles,
        "title": titles[0],
        "description": description,
        "tags": tags,
        "category_id": "27",  # Education
    }
