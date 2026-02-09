from pathlib import Path
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]
# current path: .claude/skills/email-service/scripts/send_email.py
ROOT = Path(__file__).resolve().parents[4]
TOKEN_PATH = ROOT / "authorization" / "token.json"

if not TOKEN_PATH.exists():
    raise RuntimeError(
        "Gmail is not authorized. "
        "Please run: python authorization/authorize_gmail.py"
    )

creds = Credentials.from_authorized_user_file(
    TOKEN_PATH,
    SCOPES
)