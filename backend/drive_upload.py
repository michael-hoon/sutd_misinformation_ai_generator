"""
Google Drive upload helper using OAuth 2.0 user credentials.

Uploads generated media files to a shared Google Drive folder so that
the separate detection system can pick them up for analysis.

Requires a valid token.json (created by running authorize_drive.py once).
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import GOOGLE_DRIVE_FOLDER_ID, OAUTH_TOKEN_FILE, OAUTH_CREDENTIALS_FILE

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Mime types for the media we generate
MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


def _get_drive_service():
    """Build and return an authenticated Google Drive API service."""
    token_path = Path(OAUTH_TOKEN_FILE)

    if not token_path.exists():
        raise FileNotFoundError(
            "token.json not found. Run 'python authorize_drive.py' first "
            "to complete the one-time OAuth setup."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refresh the token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist the refreshed token
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(filepath: str | Path, filename: str) -> dict:
    """
    Upload a local file to the configured Google Drive folder.

    Args:
        filepath: Absolute path to the file on disk.
        filename: The desired filename in Google Drive.

    Returns:
        dict with keys: file_id, web_view_link, filename
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    suffix = filepath.suffix.lower()
    mime_type = MIME_MAP.get(suffix, "application/octet-stream")

    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [GOOGLE_DRIVE_FOLDER_ID],
    }

    media = MediaFileUpload(str(filepath), mimetype=mime_type, resumable=True)

    uploaded = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
        )
        .execute()
    )

    return {
        "file_id": uploaded["id"],
        "web_view_link": uploaded.get("webViewLink", ""),
        "filename": filename,
    }
