def search_email(service, query: str, max_results: int = 5):
    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    return [
        {
            "message_id": msg["id"],
            "thread_id": msg["threadId"]
        }
        for msg in messages
    ]