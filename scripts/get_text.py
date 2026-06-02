from playwright.sync_api import sync_playwright
import re, sys

url = sys.argv[1] if len(sys.argv) > 1 else 'https://bigmodel.cn/glm-coding'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(url, timeout=30000)
    page.wait_for_timeout(4000)
    text = page.inner_text('body')
    browser.close()

with open('C:/Users/qw/.openclaw/workspace/scripts/page_text.txt', 'w', encoding='utf-8') as f:
    f.write(text[:4000] if text else 'No text found')
print('Done')
