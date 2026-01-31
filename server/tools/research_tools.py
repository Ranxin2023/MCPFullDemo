"""
research_tools.py

Tools for selecting and ranking web_search results before scraping.
This reduces wasted scrapes and improves answer quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP


# Light domain trust heuristics (customize for your project)
_TRUSTED_TLDS = (".gov", ".edu")
_TRUSTED_DOMAINS = [
    "weather.gov",
    "noaa.gov",
    "nws.noaa.gov",
    "cdc.gov",
    "who.int",
]
_LOW_QUALITY_HINTS = [
    "pinterest.",
    "facebook.",
    "instagram.",
    "tiktok.",
    "x.com",
    "twitter.",
]


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if len(t) >= 3]
    return tokens


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _tld_boost(dom: str) -> float:
    for tld in _TRUSTED_TLDS:
        if dom.endswith(tld):
            return 2.0
    return 0.0


def _trusted_domain_boost(dom: str) -> float:
    for td in _TRUSTED_DOMAINS:
        if td in dom:
            return 2.5
    return 0.0


def _low_quality_penalty(dom: str) -> float:
    for hint in _LOW_QUALITY_HINTS:
        if hint in dom:
            return -2.0
    return 0.0


def _keyword_overlap_score(goal_tokens: List[str], text: str) -> float:
    if not goal_tokens:
        return 0.0
    hay = set(_tokenize(text))
    overlap = sum(1 for t in goal_tokens if t in hay)
    return overlap / max(1, len(goal_tokens))


def register_research_tools(mcp: FastMCP) -> None:
    """Register research selection/ranking tools with the MCP server."""

    @mcp.tool()
    def rank_search_results(
        results: List[Dict[str, Any]],
        goal: str,
        top_k: int = 5,
        prefer_official: bool = True,
    ) -> Dict[str, Any]:
        """
        Rank web search results for scraping based on the user's goal.

        Args:
            results: List of {title, url, snippet} from web_search
            goal: The user’s intent / task (e.g., "road closures yosemite", "winter storm advisory")
            top_k: Number of top URLs to return (1-20)
            prefer_official: If True, boosts .gov/.edu and known official domains.

        Returns:
            Dict with ranked entries and top_urls.
        """
        if not isinstance(results, list) or not results:
            return {"error": "results must be a non-empty list"}

        goal_tokens = _tokenize(goal or "")
        top_k = int(top_k)
        if top_k < 1:
            top_k = 1
        elif top_k > 20:
            top_k = 20

        scored: List[Dict[str, Any]] = []

        for idx, item in enumerate(results):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()

            if not url:
                continue

            dom = _domain(url)
            score = 0.0

            # keyword relevance
            score += 3.0 * _keyword_overlap_score(goal_tokens, title)
            score += 2.0 * _keyword_overlap_score(goal_tokens, snippet)

            # domain trust
            if prefer_official:
                score += _tld_boost(dom)
                score += _trusted_domain_boost(dom)

            # penalty for low-quality / social domains
            score += _low_quality_penalty(dom)

            # small boost if url path looks article-like (often more content to scrape)
            if any(p in url.lower() for p in ["/news", "/article", "/blog", "/press", "/alerts", "/advisory"]):
                score += 0.3

            scored.append(
                {
                    "rank": None,  # fill later
                    "score": round(score, 4),
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "domain": dom,
                    "original_index": idx,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)

        for i, s in enumerate(scored):
            s["rank"] = i + 1

        top = scored[:top_k]
        top_urls = [x["url"] for x in top]

        return {
            "goal": goal,
            "top_k": top_k,
            "top_urls": top_urls,
            "ranked": top,
            "total_scored": len(scored),
        }
