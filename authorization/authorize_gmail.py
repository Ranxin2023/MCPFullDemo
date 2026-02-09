from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
# from pathlib import Path
import os
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# ROOT = Path(__file__).resolve().parents[2]
# TOKEN_PATH = "token.json"
# CREDS_PATH = "credentials.json"


def authorize():
    creds = None

    if os.path.exists("./authorization/token.json"):
        creds = Credentials.from_authorized_user_file("./authorization/token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "./authorization/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("./authorization/token.json", "w") as token:
            token.write(creds.to_json())

    print("✅ Gmail authorization complete. token.json generated.")


if __name__ == "__main__":
    authorize()
