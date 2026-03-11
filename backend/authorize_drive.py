"""
One-time OAuth 2.0 authorization for Google Drive uploads.

Run this script once from the backend directory (inside your venv):

    python authorize_drive.py

A browser window will open asking you to sign in and grant Drive
file-access permission.  The resulting token is saved to token.json
and will be used automatically by drive_upload.py for all future
uploads.  The token includes a refresh-token, so you should not
need to re-run this unless you revoke access.

Prerequisites:
    1. Create an OAuth 2.0 "Desktop app" credential in Google Cloud
       Console and download the JSON file.
    2. Save it as  backend/credentials.json
"""

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CREDENTIALS_FILE = os.getenv(
    "OAUTH_CREDENTIALS_FILE",
    str(Path(__file__).parent / "credentials.json"),
)
TOKEN_FILE = os.getenv(
    "OAUTH_TOKEN_FILE",
    str(Path(__file__).parent / "token.json"),
)


def main():
    if not Path(CREDENTIALS_FILE).exists():
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print(
            "Download your OAuth Desktop-app credentials JSON from "
            "Google Cloud Console and save it as backend/credentials.json"
        )
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Persist the token (including the refresh token)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅ Authorization successful!  Token saved to {TOKEN_FILE}")
    print("You can now start the backend — Drive uploads will work.")


if __name__ == "__main__":
    main()
