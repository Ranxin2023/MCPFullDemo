import base64
def read_email(service, message_id: str):
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    headers = msg["payload"].get("headers", [])
    header_map = {h["name"]: h["value"] for h in headers}

    body = ""

    def extract_body(payload):
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")
        elif payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8")
        return ""

    body = extract_body(msg["payload"])

    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "from": header_map.get("From"),
        "to": header_map.get("To"),
        "subject": header_map.get("Subject"),
        "date": header_map.get("Date"),
        "body": body
    }