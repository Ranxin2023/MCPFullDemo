# skills.md — Agent Skills (MCP Project)

This document defines the **agent-level skills** supported by this MCP project.
A “skill” is a behavior that may require **multiple tool calls** (not just one tool).
Each skill includes:
- what it does
- when to use it
- tools involved
- constraints (credentials, robots.txt, limits)
- example prompts

---

## 1) Location Understanding

### Skill: Geocode a user location
**Goal**  
Convert user-friendly locations (city, address, landmark) into usable coordinates.

**When to use**
- User provides: “Seattle”, “UC Davis”, “Golden Gate Bridge”
- User asks for forecast but provides no lat/lon

**Tools**
- `geocode_location(place: str) -> {latitude, longitude, display_name}` *(planned)*

**Failure handling**
- If no results: ask user for a more specific location (city + state/country)

**Example prompts**
- “What’s the weather in Seattle?”
- “Forecast near Yosemite Valley.”

---

### Skill: Resolve state from coordinates
**Goal**  
Translate coordinates to a US state code for weather alerts.

**When to use**
- User asks for alerts based on a location (not a state code)

**Tools**
- `resolve_state_from_coords(latitude: float, longitude: float) -> {state_code}` *(planned)*

**Example prompts**
- “Any weather alerts near San Jose?”
- “Alerts for my current coordinates.”

---

## 2) Weather Intelligence

### Skill: Forecast retrieval
**Goal**  
Get the next forecast periods using National Weather Service API.

**When to use**
- User asks about weather conditions for a location/time window

**Tools**
- `get_forecast(latitude: float, longitude: float) -> str`

**Notes**
- Forecast output should be summarized to be user-friendly.

**Example prompts**
- “What’s the weather like tomorrow at (37.77, -122.42)?”
- “Give me the next 5 forecast periods.”

---

### Skill: Weather alerts retrieval
**Goal**  
Get active weather alerts for a US state.

**When to use**
- User explicitly asks for warnings/advisories
- User asks “is it safe to travel / hike / drive” and location is in the US

**Tools**
- `get_alerts(state: str) -> str`

**Notes**
- Supports state full name or abbreviation (depending on your server implementation).

**Example prompts**
- “Any active alerts in California?”
- “Show current alerts for TX.”

---

## 3) Web Research

### Skill: Real-time web search
**Goal**  
Find up-to-date sources on a topic (news, advisories, closures, local conditions).

**When to use**
- User asks for “latest”, “recent”, “today”, “news”, “advisory”
- You need external context beyond weather.gov

**Tools**
- `web_search(query: str, num_results: int = 10, country: str = "us") -> dict`

**Credentials**
- Requires `BRAVE_SEARCH_API_KEY` (via env or `CredentialManager`)

**Failure handling**
- If missing credential: return actionable help message (how to set key)

**Example prompts**
- “Search for road closures near Yosemite.”
- “Any recent news about storms in Northern California?”

---

### Skill: Rank/Select the best sources from search results
**Goal**  
Choose which URLs to open/scrape based on the user’s goal.

**When to use**
- Search returns many links; agent should scrape only top candidates

**Tools**
- `rank_search_results(results: list, goal: str) -> {top_urls: list}` *(planned)*

**Heuristics**
- Prefer official domains (e.g., .gov, park sites), reputable news outlets, recently updated pages.

---

## 4) Web Reading (Scraping + Extraction)

### Skill: Scrape readable content from a page
**Goal**  
Extract clean text from a page for summarization or fact lookup.

**When to use**
- User provides a URL and asks “summarize”, “extract”, “read”
- After web_search selects a likely relevant page

**Tools**
- `web_scrape(url: str, selector: str | None = None, include_links: bool = False, max_length: int = 50000, respect_robots_txt: bool = True) -> dict`

**Safety & ethics**
- Respect `robots.txt` by default
- Skip non-HTML content (PDF/JSON/images)
- If blocked (robots/login), fall back to alternate sources or return explanation

**Example prompts**
- “Summarize this page: https://…”
- “Extract the article content only (use selector if needed).”

---

### Skill: Post-process extracted text for summarization
**Goal**  
Reduce noise and structure extracted content into a clean “briefing-ready” form.

**When to use**
- After scraping, before generating a summary/briefing

**Tools**
- `extract_main_text(content: str, max_chars: int = 12000) -> {clean_text: str}` *(planned)*

**Notes**
- Focus on readability: remove repeated nav text, compress whitespace, truncate safely.

---

## 5) Complex Multi-step Skill: Travel Weather Briefing

### Skill: Generate a travel/weather briefing for a place + time window
**Goal**  
Produce a single cohesive briefing combining:
- forecast
- alerts
- latest advisories/news (optional)
- actionable precautions

**When to use**
- User asks “Should I travel / hike / drive”
- User requests “briefing”, “risk”, “what to watch for”

**Typical tool chain**
1. `geocode_location(place)` *(planned)* → get lat/lon  
2. `get_forecast(lat, lon)` → weather outlook  
3. `resolve_state_from_coords(lat, lon)` *(planned)* → state code  
4. `get_alerts(state)` → active hazards  
5. If “latest / closures / advisory” needed:
   - `web_search(query)` → find sources
   - `rank_search_results(...)` *(planned)* → choose best links
   - `web_scrape(url)` → extract key info
   - `extract_main_text(...)` *(planned)* → clean

**Output format (recommended)**
- Overview (1–2 sentences)
- Forecast highlights (temp/wind/precip)
- Alerts (if any)
- Risks & advice (actionable)
- Sources (URLs if needed)

**Example prompts**
- “Give me a travel weather briefing for Seattle this weekend.”
- “I’m hiking Yosemite tomorrow—any alerts and what should I watch out for?”

---

## 6) Persistence & Reporting

### Skill: Save and retrieve briefings
**Goal**  
Let users save multi-step results and retrieve them later.

**When to use**
- User says “save this”, “store this”, “show my last briefing”

**Tools**
- `save_briefing(title: str, content: str, metadata: dict) -> {id: str}` *(planned)*
- `list_briefings() -> list` *(planned)*
- `get_briefing(id: str) -> dict` *(planned)*

**Example prompts**
- “Save that briefing as ‘Yosemite hike’.”
- “Show my saved briefings.”

---

## Tool boundaries & rules (recommended)

- Use `get_forecast` only when you have valid coordinates.
- Use `get_alerts` only with a valid 2-letter US state code (or normalize full names).
- Use `web_search` for recency-sensitive info (“latest”, “today”, “news”, “closures”).
- Use `web_scrape` only after selecting a specific URL; respect robots.txt by default.
- If scraping fails due to login/robots, explain why and fall back to search or alternative sources.
- Prefer official sources for safety-critical info when available.

---

## Quick capability examples

- “Forecast for (37.77, -122.42)” → `get_forecast`
- “Alerts in California” → `get_alerts`
- “Latest storm news in CA” → `web_search`
- “Summarize this URL” → `web_scrape` (+ optional post-processing)
- “Weekend travel briefing for Seattle” → multi-step pipeline (geo → forecast → alerts → research → scrape → summarize)
