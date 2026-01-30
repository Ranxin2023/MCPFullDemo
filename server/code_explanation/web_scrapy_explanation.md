# Code Explanation of `web_scrapy_tool.py`
## 1. What `register_web_scrapy_tools(mcp)` is for
## 4. Step by Step logic inside `web_scrape`
1. URL normalization
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
        - 
3. Clamp `max_length`
```py
if max_length < 1000:
    max_length = 1000
elif max_length > 500000:
    max_length = 500000

```
- This prevents:
    - too small outputs (unhelpful)
    - too huge outputs (LLM context blowup)