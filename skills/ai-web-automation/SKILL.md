---
name: ai-web-automation
description: Web Automation Service — scrape web pages, extract content, and save structured reports. Use when: scraping a URL, extracting page content, automating web data collection, or building datasets from websites.
version: 1.0.0
author: OpenClaw AI Agent
license: MIT
tags: [web, scraping, automation, extraction]
triggers:
  - "scrape this URL"
  - "extract content from"
  - "web page content"
  - "scrape the page"
  - "crawl this website"
  - "extract all links from"
required_environment_variables: []
required_commands: []
---

# Web Automation Service

Scrape web pages and extract structured content using a simple Python script.

## Usage

```bash
cd /path/to/ai-web-automation
python3 main.py scrape <url>
```

### Examples

```bash
# Scrape a single page
python3 main.py scrape https://example.com

# Scrape multiple pages (batch)
for url in https://site.com/page1 https://site.com/page2; do
  python3 main.py scrape "$url"
done
```

## Output

Results are saved to `ai-web-automation/output/` as Markdown files:

```
output/
  scrape_20250101_120000.md
  scrape_20250101_120045.md
```

Each report includes:
- URL and HTTP status code
- Page title (if detectable)
- Link count found on the page
- Timestamp

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Error: connection timeout` | Site unreachable or too slow | Increase timeout in main.py or try a different URL |
| `Error: name or service not known` | Invalid URL / DNS failure | Verify the URL is correct and accessible |
| `Error: non-UTF8 encoding` | Binary content (images, PDFs) | This tool is for HTML pages only |

## Limitations

- No JavaScript rendering (static HTML only)
- No rate limiting — be respectful when scraping
- No authentication / cookie support
- No CAPTCHA handling
- Output format is Markdown only
