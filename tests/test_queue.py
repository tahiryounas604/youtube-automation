import pytest

from youtube_automation.queue import Queue


def _queue(tmp_path):
    return Queue(str(tmp_path / "queue.json"))


def test_add_list_and_persistence(tmp_path):
    q = _queue(tmp_path)
    entry = q.add("How DNS Works", "video.mp4", "2026-11-12T10:00:00Z")
    assert entry["status"] == "queued"
    assert entry["id"]
    # A fresh Queue on the same file sees the entry (persistence).
    q2 = _queue(tmp_path)
    assert [e["id"] for e in q2.list_all()] == [entry["id"]]


def test_list_sorted_by_scheduled_time(tmp_path):
    q = _queue(tmp_path)
    q.add("Later", "b.mp4", "2026-11-13T10:00:00Z")
    q.add("Earlier", "a.mp4", "2026-11-12T10:00:00Z")
    assert [e["topic"] for e in q.list_all()] == ["Earlier", "Later"]


def test_update_status_and_due(tmp_path):
    q = _queue(tmp_path)
    past = q.add("Past", "a.mp4", "2026-11-01T10:00:00Z")
    future = q.add("Future", "b.mp4", "2027-01-01T10:00:00Z")
    due = q.due(now="2026-11-12T00:00:00Z")
    assert [e["id"] for e in due] == [past["id"]]
    assert future["id"] not in [e["id"] for e in due]
    q.update_status(past["id"], "done")
    assert q.due(now="2026-11-12T00:00:00Z") == []
    assert q.list_all(status="done")[0]["id"] == past["id"]


def test_queue_rejects_bad_input(tmp_path):
    q = _queue(tmp_path)
    with pytest.raises(ValueError):
        q.add("", "a.mp4", "2026-11-12T10:00:00Z")
    with pytest.raises(ValueError):
        q.add("Topic", "a.mp4", "not-a-date")
    entry = q.add("Topic", "a.mp4", "2026-11-12T10:00:00Z")
    with pytest.raises(ValueError):
        q.update_status(entry["id"], "bogus")
    with pytest.raises(KeyError):
        q.update_status("missing-id", "done")


def test_remove(tmp_path):
    q = _queue(tmp_path)
    entry = q.add("Topic", "a.mp4", "2026-11-12T10:00:00Z")
    assert q.remove(entry["id"]) is True
    assert q.remove(entry["id"]) is False
    assert q.list_all() == []
