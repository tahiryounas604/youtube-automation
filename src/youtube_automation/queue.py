"""Scheduling queue: a JSON file of planned videos and their status.

Each entry: ``{"id", "topic", "video_path", "scheduled_at" (ISO 8601),
"status", "created_at", "note"}``. Statuses: ``queued``,
``processing``, ``done``, ``failed``. The queue is loaded from disk on
every operation and saved after every mutation, so a crash never loses
more than the in-flight change.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

STATUSES = ("queued", "processing", "done", "failed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: str) -> datetime:
    """Parse an ISO-8601 timestamp (``Z`` accepted) into an aware datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Queue:
    """A JSON-backed video scheduling queue."""

    def __init__(self, path: str):
        self.path = path
        self.entries: list[dict] = []
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise ValueError("queue file must contain a JSON list")
            self.entries = data

    def save(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.entries, fh, indent=2)
        os.replace(tmp, self.path)

    def add(
        self,
        topic: str,
        video_path: str,
        scheduled_at: str,
        metadata_path: str | None = None,
    ) -> dict:
        """Schedule a video. Returns the created entry."""
        topic = topic.strip()
        if not topic:
            raise ValueError("topic must not be empty")
        parse_time(scheduled_at)  # validates the timestamp
        entry = {
            "id": uuid.uuid4().hex[:12],
            "topic": topic,
            "video_path": video_path,
            "scheduled_at": scheduled_at,
            "status": "queued",
            "created_at": _now_iso(),
            "metadata_path": metadata_path,
            "note": "",
        }
        self.entries.append(entry)
        self.save()
        return entry

    def get(self, entry_id: str) -> dict | None:
        for entry in self.entries:
            if entry["id"] == entry_id:
                return entry
        return None

    def list_all(self, status: str | None = None) -> list[dict]:
        entries = sorted(self.entries, key=lambda e: e["scheduled_at"])
        if status:
            if status not in STATUSES:
                raise ValueError(f"unknown status: {status}")
            entries = [e for e in entries if e["status"] == status]
        return entries

    def update_status(self, entry_id: str, status: str, note: str = "") -> dict:
        """Set an entry's status. Returns the updated entry."""
        if status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(f"no queue entry with id {entry_id}")
        entry["status"] = status
        entry["note"] = note
        self.save()
        return entry

    def due(self, now: str | None = None) -> list[dict]:
        """Queued entries whose scheduled time has arrived, oldest first."""
        moment = parse_time(now) if now else datetime.now(timezone.utc)
        return [
            e
            for e in self.list_all(status="queued")
            if parse_time(e["scheduled_at"]) <= moment
        ]

    def remove(self, entry_id: str) -> bool:
        """Delete an entry. Returns True when something was removed."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        if len(self.entries) != before:
            self.save()
            return True
        return False
