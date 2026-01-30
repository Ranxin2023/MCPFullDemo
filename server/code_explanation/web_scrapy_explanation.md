# Code Explanation of `web_scrapy_tool.py`
## 1. What `register_web_scrapy_tools(mcp)` is for
- **The function signature**
```py
def register_web_scrapy_tools(mcp: FastMCP) -> None:
    """Register web scrape tools with the MCP server."""

```
- This is a registration wrapper:
    - You create `mcp = FastMCP("...")` somewhere else
    - Then you call `register_web_scrapy_tools(mcp)`
    - That call **registers tools** (functions decorated with `@mcp.tool()`) onto the server instance
## 2. The tool that gets registered: `web_scrape(...)`
- Inside `register_web_scrapy_tools`, you define:
```py
@mcp.tool()
def web_scrape(
    url: str,
    selector: str | None = None,
    include_links: bool = False,
    max_length: int = 50000,
    respect_robots_txt: bool = True,
) -> dict:

```
- What `@mcp.tool()` does
    - It tells FastMCP: “Expose this function as an MCP tool.”
- So when your client calls list_tools(), this tool appears as:
    - **name**: `web_scrape`
    - **description**: taken from the docstring
    - **input schema**: inferred from type hints (`url`, `selector`, etc.)
- That’s how the LLM learns how to call it. 
## 3. Parameters (why they exist)
- Inside web_scrape, the parameters are designed for LLM/agent use:
    - `url`: target webpage to fetch
    - `selector`: optional CSS selector to extract only specific content (like `"article"` or `".main-content"`)
    - `include_links`: if True, returns up to ~50 `<a href>` links
    - `max_length`: truncates extracted text so tool output doesn’t explode (default 50k chars)
    - `respect_robots_txt`: ethical scraping toggle; blocks scraping if robots disallows it
## 4. Step by Step logic inside `web_scrape`
1. **URL normalization**
```py
if not url.startswith(("http://", "https://")):
    url = "https://" + url

```
2. robots.txt check (if enabled)
```py
if respect_robots_txt:
    allowed, reason = _is_allowed_by_robots(url)
    if not allowed:
        return {
            "error": f"Scraping blocked: {reason}",
            "blocked_by_robots_txt": True,
            "url": url,
        }

```
- **What `_is_allowed_by_robots` does (important)**
    - It parses the URL, extracts base domain and path
    - It loads/caches the site’s `robots.txt`
    - Then it checks permission using:
        - your bot UA (`USER_AGENT`)
        - and wildcard `"*"`
    - If blocked, the tool returns a structured “blocked” error instead of throwing.
- **robots.txt caching**
    - You have a module-level cache:
    ```py
        _robots_cache: dict[str, RobotFileParser | None] = {}

    ```
    - So if you scrape multiple pages from the same domain, you don’t fetch `robots.txt` every time.
3. **Clamp `max_length`**
```py
if max_length < 1000:
    max_length = 1000
elif max_length > 500000:
    max_length = 500000

```
- This prevents:
    - too small outputs (unhelpful)
    - too huge outputs (LLM context blowup)
4. **Fetch the webpage (HTTP GET)**
```py
response = httpx.get(
    url,
    headers={
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,...",
        "Accept-Language": "en-US,en;q=0.5",
    },
    follow_redirects=True,
    timeout=30.0,
)

```
- Key design choices:
    - Uses a **browser-like User-Agent** (`BROWSER_USER_AGENT`) so sites serve normal HTML
    - Uses `follow_redirects=True` so shortened/redirected links still work
    - Uses a timeout so the tool never hangs forever

5. **Status code handling**
```py
if response.status_code != 200:
    return {"error": f"HTTP {response.status_code}: Failed to fetch URL"}

```
- Again: tool returns a dict error (agent-safe), not an exception.

6. **Content-Type validation (your “START FIX”)**
```py
content_type = response.headers.get("content-type", "").lower()
if not any(t in content_type for t in ["text/html", "application/xhtml+xml"]):
    return {
        "error": f"Skipping non-HTML content (Content-Type: {content_type})",
        "url": url,
        "skipped": True
    }

```
- This is a really good guardrail because otherwise BeautifulSoup might try to “parse”:
    - JSON APIs
    - PDFs
    - images
    - binaries
- …and you’d get garbage outputs or crashes.

7. **Parse HTML + remove noise**
```py
soup = BeautifulSoup(response.text, "html.parser")

for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
    tag.decompose()

```
- This improves extracted text quality by removing:
    - scripts/styles
    - navigation / header/footer boilerplate
    - sidebars / iframes

8. Extract title + meta description
```py
title_tag = soup.find("title")
...
meta_desc = soup.find("meta", attrs={"name": "description"})

```
- These fields help LLMs orient the content (and are useful for citation-like summaries).
