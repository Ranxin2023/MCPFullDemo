"""
storage_tools.py

Simple persistence for "briefings" and reports.
Stores records in a JSON file with atomic writes.

This is intentionally lightweight so it works anywhere without extra deps.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP


def _now_iso() -> str:
    # ISO-ish timestamp (UTC not guaranteed unless you enforce it; fine for local dev)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"briefings": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt file fallback
        return {"briefings": []}


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def register_storage_tools(
    mcp: FastMCP,
    storage_path: str = "data/briefings.json",
) -> None:
    """
    Register storage tools.

    Args:
        storage_path: relative or absolute path to the JSON storage file.
                     Default: data/briefings.json (in project working dir).
    """
    db_path = Path(storage_path)

    @mcp.tool()
    def save_briefing(
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save a briefing/report to local storage.

        Args:
            title: Briefing title
            content: The text content (briefing body)
            metadata: Optional metadata dict (location, coords, urls, etc.)
            tags: Optional list of tags

        Returns:
            {id, title, created_at}
        """
        if not isinstance(title, str) or not title.strip():
            return {"error": "title must be a non-empty string"}
        if not isinstance(content, str) or not content.strip():
            return {"error": "content must be a non-empty string"}

        record_id = uuid.uuid4().hex
        created_at = _now_iso()
        record = {
            "id": record_id,
            "title": title.strip(),
            "content": content.strip(),
            "metadata": metadata or {},
            "tags": tags or [],
            "created_at": created_at,
            "updated_at": created_at,
        }

        db = _safe_read_json(db_path)
        briefings = db.get("briefings", [])
        if not isinstance(briefings, list):
            briefings = []
        briefings.insert(0, record)  # newest first
        db["briefings"] = briefings

        try:
            _atomic_write_json(db_path, db)
        except Exception as e:
            return {"error": f"failed to save briefing: {str(e)}"}

        return {"id": record_id, "title": record["title"], "created_at": created_at}

    @mcp.tool()
    def list_briefings(
        limit: int = 20,
        tag: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List saved briefings.

        Args:
            limit: max number of results (1-200)
            tag: optional filter by tag
            query: optional substring search in title/content

        Returns:
            {total, items:[{id,title,created_at,tags,metadata_preview}]}
        """
        limit = int(limit)
        if limit < 1:
            limit = 1
        elif limit > 200:
            limit = 200

        db = _safe_read_json(db_path)
        briefings = db.get("briefings", [])
        if not isinstance(briefings, list):
            briefings = []

        q = (query or "").strip().lower()
        t = (tag or "").strip().lower()

        def matches(b: Dict[str, Any]) -> bool:
            if t:
                tags = [str(x).lower() for x in (b.get("tags") or [])]
                if t not in tags:
                    return False
            if q:
                title = str(b.get("title", "")).lower()
                content = str(b.get("content", "")).lower()
                if q not in title and q not in content:
                    return False
            return True

        filtered = [b for b in briefings if isinstance(b, dict) and matches(b)]
        items = []
        for b in filtered[:limit]:
            items.append(
                {
                    "id": b.get("id"),
                    "title": b.get("title"),
                    "created_at": b.get("created_at"),
                    "updated_at": b.get("updated_at"),
                    "tags": b.get("tags", []),
                    "metadata_preview": b.get("metadata", {}),
                }
            )

        return {"total": len(filtered), "limit": limit, "items": items}

    @mcp.tool()
    def get_briefing(id: str) -> Dict[str, Any]:
        """
        Retrieve a saved briefing by id.

        Args:
            id: briefing id

        Returns:
            Full record (id, title, content, metadata, tags, timestamps)
        """
        if not isinstance(id, str) or not id.strip():
            return {"error": "id must be a non-empty string"}

        db = _safe_read_json(db_path)
        briefings = db.get("briefings", [])
        if not isinstance(briefings, list):
            return {"error": "storage is corrupted or empty"}

        for b in briefings:
            if isinstance(b, dict) and b.get("id") == id:
                return b

        return {"error": f"briefing not found: {id}"}

    @mcp.tool()
    def delete_briefing(id: str) -> Dict[str, Any]:
        """
        Delete a briefing by id.

        Args:
            id: briefing id

        Returns:
            {deleted: bool, id}
        """
        if not isinstance(id, str) or not id.strip():
            return {"error": "id must be a non-empty string"}

        db = _safe_read_json(db_path)
        briefings = db.get("briefings", [])
        if not isinstance(briefings, list):
            briefings = []

        new_list = [b for b in briefings if not (isinstance(b, dict) and b.get("id") == id)]
        deleted = len(new_list) != len(briefings)
        db["briefings"] = new_list

        try:
            _atomic_write_json(db_path, db)
        except Exception as e:
            return {"error": f"failed to delete briefing: {str(e)}"}

        return {"deleted": deleted, "id": id}
