---
name: web-scrapy
description: Provides comprehensive data extraction from a single website including metadata, images, structured data, and content
---

# Web-Scrapy Skill

## Purpose

The `web-scrapy` skill provides **comprehensive data extraction** from a single website. Unlike the `web-research` skill (which focuses on discovery across multiple sources), this skill performs deep extraction of all useful information from a target URL.

## Core Capabilities

1. **Comprehensive Metadata Extraction**
   - Open Graph tags (og:title, og:image, og:description, etc.)
   - Twitter Card metadata
   - Author information
   - Publication and modification dates
   - Keywords and canonical URLs

2. **Image Extraction**
   - All images with their src URLs
   - Alt text for accessibility context
   - Automatic conversion of relative URLs to absolute
   - Limited to top 20 images to prevent overwhelming output

3. **Structured Data Extraction**
   - JSON-LD structured data (Schema.org)
   - Product information, reviews, recipes, events, etc.
   - Graceful handling of invalid JSON

4. **Content Structure**
   - Heading hierarchy (h1-h6) for document outline
   - Main text content with noise removal
   - Link extraction with anchor text
   - CSS selector support for targeted extraction

## Tool Parameters

### web_scrape

```python
web_scrape(
    url: str,
    selector: str | None = None,
    include_links: bool = False,
    include_metadata: bool = True,
    include_images: bool = False,
    include_structured_data: bool = False,
    max_length: int = 50000,
    respect_robots_txt: bool = True,
)
```

**Parameters:**

- `url` (required): The webpage URL to scrape. Automatically adds `https://` if missing.
- `selector` (optional): CSS selector to target specific content (e.g., `'article'`, `'.main-content'`, `'#post-body'`)
- `include_links` (bool): Extract hyperlinks with anchor text (default: False)
- `include_metadata` (bool): Extract comprehensive metadata (default: True)
- `include_images` (bool): Extract images with alt text, up to 20 (default: False)
- `include_structured_data` (bool): Extract JSON-LD structured data (default: False)
- `max_length` (int): Maximum content length in characters, 1000-500000 (default: 50000)
- `respect_robots_txt` (bool): Honor robots.txt rules (default: True)

**Returns:**

```python
{
    "url": str,                    # Final URL after redirects
    "title": str,                  # Page title
    "description": str,            # Meta description
    "content": str,                # Main text content
    "length": int,                 # Content length
    "headings": [                  # Always included
        {"level": int, "text": str},
        ...
    ],
    "metadata": {                  # If include_metadata=True
        "open_graph": {...},
        "twitter_card": {...},
        "author": str,
        "published_date": str,
        "modified_date": str,
        "keywords": [str, ...],
        "canonical_url": str
    },
    "images": [                    # If include_images=True
        {"src": str, "alt": str},
        ...
    ],
    "structured_data": [           # If include_structured_data=True
        {...},  # JSON-LD objects
        ...
    ],
    "links": [                     # If include_links=True
        {"text": str, "href": str},
        ...
    ],
    "robots_txt_respected": bool
}
```

## Usage Strategies

### Strategy 1: Comprehensive Extraction (All Data)

Use when you need complete information from a page:

```python
web_scrape(
    url="https://example.com/article",
    include_metadata=True,
    include_images=True,
    include_structured_data=True,
    include_links=True
)
```

**Best for:** Blog posts, news articles, product pages, documentation

### Strategy 2: Metadata Focus

Use when you need metadata without full content:

```python
web_scrape(
    url="https://example.com/article",
    include_metadata=True,
    include_images=False,
    include_structured_data=False,
    max_length=1000  # Minimal content
)
```

**Best for:** Link preview generation, SEO analysis, social media cards

### Strategy 3: Structured Data Extraction

Use for e-commerce, recipes, events, reviews:

```python
web_scrape(
    url="https://example.com/product",
    include_structured_data=True,
    include_images=True
)
```

**Best for:** Product catalogs, recipe sites, event listings, review aggregation

### Strategy 4: Targeted Content Extraction

Use CSS selectors to extract specific sections:

```python
web_scrape(
    url="https://example.com/docs",
    selector="article.documentation",
    include_links=True,
    max_length=100000  # Large docs
)
```

**Best for:** Documentation, specific article sections, blog post content

### Strategy 5: Chained Processing with extract_main_text

Use for maximum content quality:

```python
# Step 1: Scrape with comprehensive data
result = web_scrape(
    url="https://example.com/article",
    include_metadata=True,
    include_images=True
)

# Step 2: Post-process content for better quality
cleaned = extract_main_text(
    html=result["content"],
    include_headings=True,
    include_tables=True
)
```

**Best for:** Academic papers, long-form articles, technical documentation

## Use Cases

### 1. Article Analysis
Extract full metadata, author info, publication dates, and content structure for research or archival.

### 2. Product Information Extraction
Get structured product data (price, reviews, availability) from e-commerce sites using JSON-LD.

### 3. SEO and Social Media Analysis
Extract Open Graph and Twitter Card metadata to analyze how content appears when shared.

### 4. Image Cataloging
Extract all images from a gallery or portfolio with their alt text for accessibility auditing.

### 5. Documentation Scraping
Use CSS selectors to extract specific documentation sections with heading hierarchy preserved.

### 6. Recipe Extraction
Extract JSON-LD structured recipe data (ingredients, instructions, timing) from cooking websites.

## Comparison with web-research Skill

| Feature | web-scrapy | web-research |
|---------|-----------|--------------|
| **Purpose** | Deep extraction from single URL | Discovery across multiple sources |
| **Focus** | Comprehensive data extraction | Search + summarize workflow |
| **Metadata** | Full metadata (OG, Twitter, dates) | Basic title/description |
| **Structured Data** | JSON-LD extraction | Not included |
| **Images** | Up to 20 with alt text | Not extracted |
| **Use Case** | "Extract everything from this page" | "Research this topic" |

**When to use web-scrapy:** You have a specific URL and want all its data.

**When to use web-research:** You have a topic/question and need to search and synthesize multiple sources.

## Ethical Guidelines (MANDATORY)

1. **Respect robots.txt**: Keep `respect_robots_txt=True` unless you have explicit permission
2. **Rate Limiting**: Do not scrape thousands of pages rapidly; add delays between requests
3. **User-Agent**: The tool identifies itself as a bot for transparency
4. **Copyright**: Extracted content may be copyrighted; respect intellectual property laws
5. **Terms of Service**: Check the website's TOS before scraping
6. **Personal Data**: Be cautious with pages containing personal information (GDPR, privacy laws)
7. **Login Required**: Do not attempt to bypass authentication or paywalls

## Error Handling

The tool returns error dictionaries for common issues:

```python
# Blocked by robots.txt
{"error": "Scraping blocked: ...", "blocked_by_robots_txt": True, "url": "..."}

# Invalid selector
{"error": "No elements found matching selector: ...", "url": "..."}

# Network timeout
{"error": "Request timed out"}

# Non-HTML content
{"error": "Skipping non-HTML content (Content-Type: ...)", "url": "...", "skipped": True}
```

**Always check for the `error` key** before processing results.

## Best Practices

1. **Start with defaults**: Use `include_metadata=True` by default, add flags as needed
2. **Use selectors for large pages**: Target specific sections to reduce noise and processing time
3. **Check headings first**: The `headings` array (always included) helps understand page structure
4. **Handle redirects gracefully**: The tool follows redirects automatically; check `result["url"]` for final URL
5. **Respect performance**: Images and structured data add overhead; only request when needed
6. **Combine with extract_main_text**: For best content quality, chain with post-processing
7. **Validate structured data**: JSON-LD may be malformed; check if `structured_data` key exists

## Examples

### Example 1: News Article Deep Dive

```python
result = web_scrape(
    url="https://news.example.com/breaking-story",
    include_metadata=True,
    include_images=True,
    include_links=True
)

# Access extracted data
print(f"Title: {result['title']}")
print(f"Author: {result['metadata']['author']}")
print(f"Published: {result['metadata']['published_date']}")
print(f"Images: {len(result['images'])} found")
print(f"Content: {result['content'][:500]}...")
```

### Example 2: E-commerce Product Data

```python
result = web_scrape(
    url="https://shop.example.com/product/12345",
    include_structured_data=True,
    include_images=True
)

# Extract product info from JSON-LD
if "structured_data" in result:
    for data in result["structured_data"]:
        if data.get("@type") == "Product":
            print(f"Name: {data.get('name')}")
            print(f"Price: {data.get('offers', {}).get('price')}")
            print(f"Rating: {data.get('aggregateRating', {}).get('ratingValue')}")
```

### Example 3: Documentation with Targeted Extraction

```python
result = web_scrape(
    url="https://docs.example.com/api/authentication",
    selector=".documentation-content",
    include_links=True,
    max_length=100000
)

# Get document outline from headings
print("Document Structure:")
for heading in result["headings"]:
    indent = "  " * (heading["level"] - 1)
    print(f"{indent}- {heading['text']}")
```

### Example 4: SEO Metadata Analysis

```python
result = web_scrape(
    url="https://example.com/landing-page",
    include_metadata=True,
    max_length=1000  # Just need metadata, not full content
)

# Analyze social sharing metadata
og = result["metadata"]["open_graph"]
twitter = result["metadata"]["twitter_card"]

print(f"OG Title: {og.get('title')}")
print(f"OG Image: {og.get('image')}")
print(f"Twitter Card Type: {twitter.get('card')}")
```

## Integration with Other Skills

- **web-research**: Use web-scrapy as the extraction backend after web-research identifies relevant URLs
- **travel-briefing**: Extract structured travel data (events, weather) from destination pages
- **weather-intelligence**: Extract weather metadata from forecast pages

## Technical Notes

- **Redirect Handling**: Automatically follows HTTP 301/302/303/307/308 redirects
- **Content-Type Validation**: Only processes HTML/XHTML content; skips JSON, PDF, images
- **Noise Removal**: Automatically removes script, style, nav, footer, header, aside tags
- **Relative URLs**: Images and links are converted to absolute URLs automatically
- **Main Content Detection**: Auto-detects `<article>`, `<main>`, or `.content` if no selector provided
- **Robots.txt Caching**: robots.txt is cached per domain to minimize requests

## Troubleshooting

**Problem:** Redirect errors with short URLs (bit.ly, tinyurl)
**Solution:** ✅ Fixed in current version; redirects are followed automatically

**Problem:** Getting too much content
**Solution:** Use `selector` to target specific sections, or reduce `max_length`

**Problem:** Missing metadata
**Solution:** Check if `"metadata"` key exists; not all pages have complete metadata

**Problem:** No structured data extracted
**Solution:** Verify the page actually contains JSON-LD; check `<script type="application/ld+json">`

**Problem:** Blocked by robots.txt
**Solution:** Check `blocked_by_robots_txt` in error response; respect the block or contact site owner
