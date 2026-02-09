import base64
from email.mime.text import MIMEText
from pathlib import Path
from mcp.server.fastmcp import FastMCP


def get_gmail_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    ROOT = Path(__file__).resolve().parents[2]
    # print(f"root path is{ROOT}")
    TOKEN_PATH = ROOT / "authorization" / "token.json"
    # print(f"token path is{TOKEN_PATH}")
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            "Gmail not authorized. "
            "Run: python authorization/authorize_gmail.py"
        )

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return build("gmail", "v1", credentials=creds)


def register_email_tools(mcp: FastMCP):

    @mcp.tool()
    def gmail_send_email(
        to: str,
        subject: str,
        body: str,
    ):
        """
        Send an email using Gmail API.
        """
        try:
            print("[DEBUG] GMAIL SEND_EMAIL TOOL CALLED")

            service = get_gmail_service()

            # Explicitly use UTF-8 encoding for email body
            message = MIMEText(body, _charset="utf-8")
            message["to"] = to
            message["subject"] = subject

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode("utf-8")

            sent = service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()

            return {
                "success": True,
                "message_id": sent["id"],
                "thread_id": sent["threadId"],
                "status": "Email sent successfully"
            }
        except Exception as e:
            # Ensure error messages don't contain problematic characters
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            return {
                "success": False,
                "error": error_msg,
                "status": "Failed to send email"
            }

    @mcp.tool()
    def gmail_read_email(message_id: str):
        try:
            service = get_gmail_service()

            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            headers = msg["payload"].get("headers", [])
            header_map = {h["name"]: h["value"] for h in headers}

            body = ""

            def extract_body(payload):
                try:
                    if "parts" in payload:
                        for part in payload["parts"]:
                            if part["mimeType"] == "text/plain":
                                return base64.urlsafe_b64decode(
                                    part["body"]["data"]
                                ).decode("utf-8", errors='replace')
                    elif payload.get("body", {}).get("data"):
                        return base64.urlsafe_b64decode(
                            payload["body"]["data"]
                        ).decode("utf-8", errors='replace')
                except Exception:
                    return "[Unable to decode email body]"
                return ""

            body = extract_body(msg["payload"])

            return {
                "success": True,
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "from": header_map.get("From", ""),
                "to": header_map.get("To", ""),
                "subject": header_map.get("Subject", ""),
                "date": header_map.get("Date", ""),
                "body": body
            }
        except Exception as e:
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            return {
                "success": False,
                "error": error_msg,
                "status": "Failed to read email"
            }

    @mcp.tool()
    def gmail_search_email(query: str, max_results: int = 5):
        try:
            service = get_gmail_service()

            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            return {
                "success": True,
                "count": len(messages),
                "messages": [
                    {
                        "message_id": msg["id"],
                        "thread_id": msg["threadId"]
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            return {
                "success": False,
                "error": error_msg,
                "status": "Failed to search emails"
            }

    @mcp.tool()
    def gmail_apply_label(message_id: str, label_ids: list[str]):
        try:
            service = get_gmail_service()

            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": label_ids,
                    "removeLabelIds": []
                }
            ).execute()

            return {
                "success": True,
                "message_id": message_id,
                "labels_applied": label_ids,
                "status": "Labels applied successfully"
            }
        except Exception as e:
            error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            return {
                "success": False,
                "error": error_msg,
                "status": "Failed to apply labels"
            }

if __name__ == "__main__":
    print("🚀 Testing get_gmail_service()")
    service = get_gmail_service()
    print("✅ Gmail service created:", service)