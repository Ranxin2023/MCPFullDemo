# Code Explanation of `web_search_tool.py`
## 1. Imports
```py
import httpx
import os
from mcp.server.fastmcp import FastMCP
from typing import Optional
from credentials import CredentialManager

```
### What each import does
- `httpx`: HTTP client library. Used to call Brave Search API (`httpx.get(...)`).
- `os`: used to read environment variables like `BRAVE_SEARCH_API_KEY`.
- `FastMCP`: MCP server class. You register tools onto it via `@mcp.tool()`.
- `Optional`: type hint for “can be None”.
- `CredentialManager`: your credential helper class that can fetch credentials (like API keys) in a centralized way.

## 2. Tool registration function
## 3. The MCP tool definition
- What `@mcp.tool()` does
- It tells FastMCP:
    - “Expose this function as a tool”
    - MCP will:\
        - include it in `list_tools()`
        - allow the client/LLM to call it by name (`web_search`)
        - infer input schema from type hints (`query`, `num_results`, `country`)
        - use the docstring as the tool description

- This is how Claude/LLMs “see” tools.
## 7. Input validation
```py
if not query or len(query) > 500:
    return {"error": "Query must be 1-500 characters"}

```
- Brave API expects a reasonable query length. You enforce it to avoid:
    - empty searches
    - huge prompt/LLM mistakes
    - wasted API calls
## 8. HTTP request to Brave Search
```py
response = httpx.get(
    "https://api.search.brave.com/res/v1/web/search",
    params={
        "q": query,
        "count": num_results,
        "country": country,
    },
    headers={
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    },
    timeout=30.0,
)

```
- **Key details**
    - Endpoint: Brave web search endpoint
    - **Query params**:
        - `q`: search query
        - `count`: number of results
        - `country`: localization
    - **Headers**:
        - `X-Subscription-Token`: Brave’s API auth mechanism
        - `Accept`: request JSON output
    - **timeout=30.0**:
        - prevents your server from hanging forever if Brave is slow
