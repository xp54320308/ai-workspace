from playwright.sync_api import sync_playwright
import time
from datetime import datetime

TARGET_HOUR, TARGET_MIN, TARGET_SEC = 10, 0, 0

TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX3R5cGUiOiJQRVJTT05BTCIsInVzZXJfY2hhbm5lbCI6IldFQiIsInVzZXJfaWQiOjc2MzgxMjUsInVzZXJfa2V5IjoiOGZlZTA5MzgtNmM4ZS00MDczLWFhY2EtYTcwZWI0ZWRkYzk1IiwiY3VzdG9tZXJfaWQiOiIxNDgxMTc3NTQ1MDAwOTc4NyIsInVzZXJuYW1lIjoiaHhjZGZ5NzAifQ.GscpSxZUeik3ZTNa_baZF9HRh99R3UXjlW5EwqFh8gpZB3qvM7OQh4HhoDZ_cM_Ia20XqOnQHfluH_BqsiTyVw"

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)

log("=== GLM 抢兑脚本 最终版 ===")

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
    
    # 记录初始按钮状态
    log("=== 初始按钮状态 ===")
    try:
        btns = page.query_selector_all('button')
        for btn in btns:
            txt = btn.inner_text().strip()
            disabled = btn.get_attribute('disabled')
            if '售罄' in txt or '订阅' in txt or 'Pro' in txt or '连续' in txt:
                log(f"  [{txt}] disabled={disabled is not None}")
    except:
        pass

    # ---- 等待 09:59:50 ----
    log("等待 09:59:50...")
    while True:
        now = datetime.now()
        t = TARGET_HOUR * 3600 + TARGET_MIN * 60 + TARGET_SEC
        n = now.hour * 3600 + now.minute * 60 + now.second
        diff = t - n
        if diff <= 10:
            log(f">>> 进入最后10秒！({now.strftime('%H:%M:%S')})")
            break
        time.sleep(1)

    # ---- 核心：10:00 后 50ms 高频轮询 + 每5秒刷新 ----
    log("开始抢兑！高频检测...")
    clicked = False
    start = time.time()
    last_refresh = start
    
    TARGET_KEYWORDS = ['连续包季', '订阅', 'Pro', '购买', '立即', '包季']

    while not clicked and (time.time() - start) < 60:
        now_str = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        elapsed = int(time.time() - start)
        
        # 每5秒强制刷新（补货可能靠服务端轮询）
        if time.time() - last_refresh > 5:
            log(f"[{elapsed}s] 刷新页面...")
            page.reload()
            page.wait_for_timeout(300)
            last_refresh = time.time()
        
        try:
            btns = page.query_selector_all('button')
            for btn in btns:
                try:
                    txt = btn.inner_text().strip()
                    if not txt:
                        continue
                    
                    disabled = btn.get_attribute('disabled')
                    is_disabled = disabled is not None
                    has_keyword = any(k in txt for k in TARGET_KEYWORDS)
                    can_click = not is_disabled
                    
                    # 每10秒打印一次按钮状态
                    if elapsed % 10 == 0 and elapsed > 0:
                        log(f"[{elapsed}s] '{txt}' disabled={is_disabled}")
                    
                    if has_keyword and can_click:
                        log(f">>> 可点击！立即点击: '{txt}' at {now_str}")
                        btn.click()
                        clicked = True
                        page.wait_for_timeout(2000)
                        page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/01_clicked.png')
                        log("已截图 01_clicked.png")
                        break
                except:
                    pass
        except Exception as e:
            log(f"出错: {e}")
        
        time.sleep(0.05)

    if not clicked:
        log("60秒未抢到，截图记录")
        page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/02_failed.png')
    
    # ---- 处理后续：验证 + 支付 ----
    log("等待后续页面...")
    page.wait_for_timeout(5000)
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/03_after.png')
    
    try:
        txt = page.inner_text('body')
        with open('C:/Users/qw/.openclaw/workspace/scripts/post_click.txt', 'w', encoding='utf-8') as f:
            f.write(txt)
        log(f"页面内容已保存: {txt[:300]}")
    except:
        pass
    
    browser.close()
    log("=== 脚本执行完毕 ===")
    log("查看截图和 post_click.txt，了解后续状态")
