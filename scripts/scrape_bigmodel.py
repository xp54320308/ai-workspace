from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://bigmodel.cn/glm-coding', timeout=30000)
    page.wait_for_timeout(3000)
    content = page.content()
    browser.close()

content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.I|re.S)
content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.I|re.S)
text = re.sub(r'<[^>]+>', ' ', content)
text = re.sub(r'\s+', ' ', text).strip()
print(text[:3000])
