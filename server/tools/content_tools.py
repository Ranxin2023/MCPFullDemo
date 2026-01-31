"""
content_tools.py

Post-processing tools for scraped text content.

These tools do NOT fetch the web.
They clean and normalize text you already scraped with web_scrape().
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP


# Common boilerplate / noise patterns found in scraped pages
_NOISE_PATTERNS = [
    r"\bcookie\b",
    r"\bcookies\b",
    r"\bprivacy policy\b",
    r"\bterms of service\b",
    r"\baccept all\b",
    r"\bsubscribe\b",
    r"\bsign in\b",
    r"\blog in\b",
    r"\bnewsletter\b",
    r"\bshare\b",
    r"\bfacebook\b",
    r"\btwitter\b",
    r"\binstagram\b",
    r"\blinkedin\b",
    r"\bdownload our app\b",
]

# Lines with extremely low information density often look like nav / footer
_MIN_LINE_CHARS = 25


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse excessive spaces
    text = re.sub(r"[ \t]+", " ", text)
    # collapse >2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_lines(text: str) -> List[str]:
    # Preserve paragraphs but still allow line-based filtering
    lines = [ln.strip() for ln in text.split("\n")]
    # remove empty lines
    return [ln for ln in lines if ln]


def _looks_like_noise(line: str) -> bool:
    low = line.lower()
    if len(line) < _MIN_LINE_CHARS:
        # short lines are often menu items / crumbs
        # but keep short lines if they look like real sentences
        if line.endswith((".", "?", "!")):
            return False
        return True

    # too many separators / nav-like patterns
    if low.count("|") >= 3 or low.count("•") >= 3:
        return True

    # mostly uppercase (often nav / section headers) - keep some but filter extreme
    letters = [c for c in line if c.isalpha()]
    if letters:
        upper_ratio = sum(c.isupper() for c in letters) / max(1, len(letters))
        if upper_ratio > 0.85 and len(line) < 120:
            return True

    # matches common noise patterns
    for pat in _NOISE_PATTERNS:
        if re.search(pat, low):
            # Don't remove if it appears in a normal sentence-length paragraph
            if len(line) < 160:
                return True

    return False


def _truncate_safely(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    # try to cut at the end of a sentence / paragraph
    last_break = max(cut.rfind("\n\n"), cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if last_break > max_chars * 0.6:
        cut = cut[: last_break + 1]
    return cut.strip() + "\n\n...[truncated]"


def register_content_tools(mcp: FastMCP) -> None:
    """Register content post-processing tools with the MCP server."""

    @mcp.tool()
    def extract_main_text(
        content: str,
        max_chars: int = 12000,
        keep_paragraphs: bool = True,
        remove_noise: bool = True,
    ) -> Dict[str, Any]:
        """
        Clean and normalize scraped text for summarization / briefing.

        Args:
            content: Raw text content (e.g., web_scrape()['content'])
            max_chars: Maximum output length (500 - 200000)
            keep_paragraphs: If True, preserves paragraph breaks; otherwise returns one block.
            remove_noise: If True, filters boilerplate/nav/footer-like lines.

        Returns:
            Dict with cleaned text and stats.
        """
        if not isinstance(content, str) or not content.strip():
            return {"error": "content must be a non-empty string"}

        max_chars = int(max_chars)
        if max_chars < 500:
            max_chars = 500
        elif max_chars > 200000:
            max_chars = 200000

        text = _normalize_whitespace(content)

        if remove_noise:
            lines = _split_lines(text)
            filtered = [ln for ln in lines if not _looks_like_noise(ln)]
            # Rebuild while keeping paragraph-ish separation
            text = "\n\n".join(filtered).strip()

        if not text:
            return {
                "clean_text": "",
                "length": 0,
                "removed_noise": remove_noise,
                "note": "All content filtered out as noise. Try remove_noise=false.",
            }

        if not keep_paragraphs:
            text = " ".join(text.split())

        text = _truncate_safely(text, max_chars)

        return {
            "clean_text": text,
            "length": len(text),
            "removed_noise": remove_noise,
            "kept_paragraphs": keep_paragraphs,
            "max_chars": max_chars,
        }
