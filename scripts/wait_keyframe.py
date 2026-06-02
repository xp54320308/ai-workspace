import json, urllib.request, time
pid = '4254b821-293c-4076-a2e8-a41d96278b23'
for i in range(30):
    req = urllib.request.Request('http://127.0.0.1:8188/history')
    resp = urllib.request.urlopen(req, timeout=10)
    history = json.loads(resp.read())
    if pid in history:
        outputs = history[pid].get('outputs', {})
        imgs = outputs.get('9', {}).get('images', [])
        print(f'DONE: {imgs}', flush=True)
        break
    req2 = urllib.request.Request('http://127.0.0.1:8188/queue')
    resp2 = urllib.request.urlopen(req2, timeout=10)
    q = json.loads(resp2.read())
    running = len(q.get('queue_running', []))
    print(f'[{i*10}s] Running: {running}', flush=True)
    time.sleep(10)
