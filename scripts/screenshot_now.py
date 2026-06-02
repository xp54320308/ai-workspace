from playwright.sync_api import sync_playwright

TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX3R5cGUiOiJQRVJTT05BTCIsInVzZXJfY2hhbm5lbCI6IldFQiIsInVzZXJfaWQiOjc2MzgxMjUsInVzZXJfa2V5IjoiOGZlZTA5MzgtNmM4ZS00MDczLWFhY2EtYTcwZWI0ZWRkYzk1IiwiY3VzdG9tZXJfaWQiOiIxNDgxMTc3NTQ1MDAwOTc4NyIsInVzZXJuYW1lIjoiaHhjZGZ5NzAifQ.GscpSxZUeik3ZTNa_baZF9HRh99R3UXjlW5EwqFh8gpZB3qvM7OQh4HhoDZ_cM_Ia20XqOnQHfluH_BqsiTyVw"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
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
    page.goto('https://bigmodel.cn/glm-coding', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path='C:/Users/qw/.openclaw/workspace/scripts/now.png')
    
    # 获取所有按钮文字
    btns = page.query_selector_all('button')
    for btn in btns:
        txt = btn.inner_text().strip()
        disabled = btn.get_attribute('disabled')
        print(f"按钮: [{txt}] | disabled={disabled is not None}")
    
    # 获取页面文字
    txt = page.inner_text('body')
    print("=== 页面内容 ===")
    print(txt[:500])
    
    browser.close()
