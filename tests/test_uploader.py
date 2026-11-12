import pytest

from youtube_automation.uploader import build_video_body, upload_video


def test_build_video_body_shape():
    body = build_video_body("My Title", "My description", tags=["dns", "how to"])
    assert body["snippet"]["title"] == "My Title"
    assert body["snippet"]["description"] == "My description"
    assert body["snippet"]["tags"] == ["dns", "how to"]
    assert body["snippet"]["categoryId"] == "27"
    assert body["status"]["privacyStatus"] == "private"  # safe default


def test_build_video_body_rejects_bad_input():
    with pytest.raises(ValueError):
        build_video_body("", "desc")
    with pytest.raises(ValueError):
        build_video_body("x" * 101, "desc")
    with pytest.raises(ValueError):
        build_video_body("Title", "desc", privacy_status="everyone")


def test_upload_fails_fast_without_credentials(tmp_path):
    """No network call: missing credentials file must fail first."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    with pytest.raises(FileNotFoundError, match="client_secrets.json"):
        upload_video(str(video), "Title", "desc",
                     credentials_path=str(tmp_path / "client_secrets.json"))


def test_upload_fails_fast_without_video(tmp_path):
    with pytest.raises(FileNotFoundError, match="video file not found"):
        upload_video(str(tmp_path / "missing.mp4"), "Title", "desc")
