from playwright.sync_api import sync_playwright
import time, random
from datetime import datetime

TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX3R5cGUiOiJQRVJTT05BTCIsInVzZXJfY2hhbm5lbCI6IldFQiIsInVzZXJfaWQiOjc2MzgxMjUsInVzZXJfa2V5IjoiOGZlZTA5MzgtNmM4ZS00MDczLWFhY2EtYTcwZWI0ZWRkYzk1IiwiY3VzdG9tZXJfaWQiOiIxNDgxMTc3NTQ1MDAwOTc4NyIsInVzZXJuYW1lIjoiaHhjZGZ5NzAifQ.GscpSxZUeik3ZTNa_baZF9HRh99R3UXjlW5EwqFh8gpZB3qvM7OQh4HhoDZ_cM_Ia20XqOnQHfluH_BqsiTyVw"

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{ts}] {msg}", flush=True)

log("=== 诊断 + 抢兑 ===")

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
    
    # 检查当前状态
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/current_state.png')
    
    found_btn = None
    btns = page.query_selector_all('button')
    for btn in btns:
        txt = btn.inner_text().strip()
        disabled = btn.get_attribute('disabled')
        log(f"按钮: [{txt}] | disabled={disabled is not None}")
        if '售罄' in txt or '连续包季' in txt or '订阅' in txt:
            found_btn = (btn, txt, disabled is not None)
    
    log(f"当前状态: {found_btn[1] if found_btn else 'N/A'}, disabled={found_btn[2] if found_btn else 'N/A'}")
    
    if found_btn and not found_btn[2]:
        log("!!! 按钮可点击！立即抢购！")
        found_btn[0].click()
        page.wait_for_timeout(3000)
        page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/grabbed.png')
        txt = page.inner_text('body')
        with open('C:/Users/qw/.openclaw/workspace/scripts/grabbed.txt', 'w', encoding='utf-8') as f:
            f.write(txt)
        log(f"结果: {txt[:300]}")
    else:
        log("按钮仍禁用，开始随机刷新策略...")
        # 随机刷新策略：0.5-2秒随机间隔，30次
        for i in range(30):
            wait = random.uniform(0.5, 2.0)
            log(f"等待 {wait:.1f}s...")
            time.sleep(wait)
            
            page.reload()
            page.wait_for_timeout(1000)
            
            btns = page.query_selector_all('button')
            for btn in btns:
                txt = btn.inner_text().strip()
                disabled = btn.get_attribute('disabled')
                if ('连续包季' in txt or '订阅' in txt) and not (disabled is not None):
                    log(f">>> 可购买！点击: [{txt}]")
                    btn.click()
                    page.wait_for_timeout(3000)
                    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/grabbed.png')
                    txt2 = page.inner_text('body')
                    with open('C:/Users/qw/.openclaw/workspace/scripts/grabbed.txt', 'w', encoding='utf-8') as f:
                        f.write(txt2)
                    log(f"结果: {txt2[:300]}")
                    break
            else:
                continue
            break
        
        page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/final.png')
    
    browser.close()
    log("=== 完成 ===")
