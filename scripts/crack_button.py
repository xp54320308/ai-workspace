from playwright.sync_api import sync_playwright
import time
from datetime import datetime

TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX3R5cGUiOiJQRVJTT05BTCIsInVzZXJfY2hhbm5lbCI6IldFQiIsInVzZXJfaWQiOjc2MzgxMjUsInVzZXJfa2V5IjoiOGZlZTA5MzgtNmM4ZS00MDczLWFhY2EtYTcwZWI0ZWRkYzk1IiwiY3VzdG9tZXJfaWQiOiIxNDgxMTc3NTQ1MDAwOTc4NyIsInVzZXJuYW1lIjoiaHhjZGZ5NzAifQ.GscpSxZUeik3ZTNa_baZF9HRh99R3UXjlW5EwqFh8gpZB3qvM7OQh4HhoDZ_cM_Ia20XqOnQHfluH_BqsiTyVw"

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{ts}] {msg}", flush=True)

log("=== 破解 disabled 属性 ===")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={'width': 1280, 'height': 900},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
    )
    context.add_cookies([{
        'name': 'bigmodel_token_production',
        'value': TOKEN,
        'domain': '.bigmodel.cn', 'path': '/'
    }])

    page = context.new_page()
    log("打开页面...")
    page.goto('https://bigmodel.cn/glm-coding', timeout=30000)
    page.wait_for_timeout(2000)
    
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/before_crack.png')
    log("截图 before_crack.png")

    # 强制移除 disabled 属性
    log("移除 disabled 属性...")
    page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            btns.forEach(btn => {
                if (btn.innerText.includes('暂时售罄') || btn.innerText.includes('04月29日')) {
                    btn.removeAttribute('disabled');
                    btn.classList.remove('is-disabled', 'disabled');
                    btn.removeAttribute('aria-disabled');
                    console.log('已破解按钮:', btn.innerText);
                }
            });
        }
    """)
    
    page.wait_for_timeout(500)
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/after_crack.png')
    log("截图 after_crack.png")

    # 点击破解后的按钮
    log("点击按钮...")
    try:
        page.evaluate("""
            () => {
                const btns = document.querySelectorAll('button');
                btns.forEach(btn => {
                    if (btn.innerText.includes('暂时售罄') || btn.innerText.includes('04月29日')) {
                        btn.click();
                        console.log('已点击:', btn.innerText);
                    }
                });
            }
        """)
    except Exception as e:
        log(f"点击出错: {e}")
    
    page.wait_for_timeout(3000)
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/after_click.png')
    log("截图 after_click.png")
    
    try:
        txt = page.inner_text('body')
        with open('C:/Users/qw/.openclaw/workspace/scripts/after_click.txt', 'w', encoding='utf-8') as f:
            f.write(txt)
        log(f"结果: {txt[:300]}")
    except:
        pass
    
    browser.close()
    log("=== 完成 ===")
