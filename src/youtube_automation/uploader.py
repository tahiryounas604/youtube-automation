"""YouTube Data API v3 uploader.

Real upload code path using the official Google API client — but a
live upload has NOT been tested: it needs the creator's own OAuth
credentials (``client_secrets.json`` from Google Cloud Console) and a
real YouTube channel, neither of which exists in this repo. See
README.md ("Upload setup") for the steps. No credentials are stored
here, ever.

``build_video_body`` is pure and unit-tested; :func:`upload_video`
fails fast with a clear error when the video file, the credentials
file, or the Google client library is missing — before any network
call is made.
"""

from __future__ import annotations

import os

DEFAULT_CATEGORY_ID = "27"  # Education
DEFAULT_PRIVACY = "private"  # safest default: upload private, publish manually


def build_video_body(
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = DEFAULT_CATEGORY_ID,
    privacy_status: str = DEFAULT_PRIVACY,
) -> dict:
    """Build the ``videos.insert`` request body (snippet + status)."""
    title = title.strip()
    if not title:
        raise ValueError("title must not be empty")
    if len(title) > 100:
        raise ValueError("title exceeds YouTube's 100-character limit")
    if privacy_status not in ("private", "unlisted", "public"):
        raise ValueError("privacy_status must be 'private', 'unlisted' or 'public'")
    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags or []),
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy_status},
    }


def get_authenticated_service(credentials_path: str, token_path: str):
    """Build an authenticated YouTube API service (OAuth 2.0).

    Lazy-imports the Google client libraries so the rest of the
    package works without them. Raises RuntimeError with install
    instructions when the libraries are missing, and FileNotFoundError
    when the credentials file is missing.
    """
    if not os.path.isfile(credentials_path):
        raise FileNotFoundError(
            f"YouTube OAuth client file not found: {credentials_path}. "
            "Create OAuth 2.0 credentials in Google Cloud Console "
            "(APIs & Services > Credentials), download the JSON, and save it "
            "as client_secrets.json. See README.md 'Upload setup'."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - depends on optional deps
        raise RuntimeError(
            "Google API client libraries are not installed. Install them with:\n"
            "  pip install --break-system-packages "
            "google-api-python-client google-auth-oauthlib google-auth-httplib2"
        ) from exc

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if os.path.isfile(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = DEFAULT_CATEGORY_ID,
    privacy_status: str = DEFAULT_PRIVACY,
    credentials_path: str = "client_secrets.json",
    token_path: str = "token.json",
    thumbnail_path: str | None = None,
) -> dict:
    """Upload *video_path* to YouTube (resumable upload).

    Returns the API response dict (contains the new video ``id``).
    NOTE: live upload is NOT tested — see the module docstring.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"video file not found: {video_path}")
    if thumbnail_path and not os.path.isfile(thumbnail_path):
        raise FileNotFoundError(f"thumbnail file not found: {thumbnail_path}")

    youtube = get_authenticated_service(credentials_path, token_path)
    body = build_video_body(title, description, tags, category_id, privacy_status)
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(video_path, chunksize=1024 * 1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    if thumbnail_path:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()
    return {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy_status": privacy_status}
