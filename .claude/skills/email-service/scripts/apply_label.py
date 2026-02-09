def apply_label(service, message_id: str, label_ids: list[str]):
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": label_ids,
            "removeLabelIds": []
        }
    ).execute()

    return {
        "message_id": message_id,
        "labels_applied": label_ids
    }
