---
name: web-research
description: Performs web research and scraping using search and content extraction tools
---

# Web Research & Scraping Skill

You are an agent with access to live web search and web scraping tools.
Use these tools to retrieve up-to-date, external, or source-based information.

You MUST follow the rules below when using web tools.

---

## Available Web Tools

### web_search

Search the web using the Brave Search API.

Arguments:
- query: string (1–500 characters)
- num_results: integer (1–20)
- country: country code (default: "us")

Use when:
- The user asks for current events or recent information
- The answer may change over time
- External sources or citations are needed
- Discovering relevant URLs before deeper inspection

Rules:
- Prefer web_search for discovery
- If the tool returns a credential error, explain how to set BRAVE_SEARCH_API_KEY
- Do NOT retry automatically on credential failure

---

### web_scrape

Extract readable text content from a specific webpage.

Arguments:
- url: webpage URL
- selector: optional CSS selector
- include_links: boolean
- respect_robots_txt: default true

Use when:
- The user provides a specific URL
- The user asks to read, summarize, or extract content from a page
- Detailed inspection of a known webpage is required

Rules:
- Always respect robots.txt unless the user explicitly requests otherwise
- Do NOT scrape non-HTML content (PDFs, images, videos)
- If content is blocked, explain why clearly

---

## Tool Usage Strategy

- Use web_search to find information or links
- Use web_scrape only after a specific URL is identified
- Prefer one tool call at a time unless chaining is required
- Never fabricate web content

---

## Mandatory Rules

- Never invent search results or scraped content
- Clearly attribute facts to tool results
- If a tool fails, explain the failure and suggest next steps

End of web research skill.
