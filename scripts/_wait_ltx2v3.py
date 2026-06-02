import urllib.request, json, time

pid = '61d8c2a1-6b69-4e70-a5c1-ef471f5ed08d'
for i in range(180):
    try:
        h = json.loads(urllib.request.urlopen(f'http://127.0.0.1:8188/history/{pid}', timeout=5).read())
        if pid in h:
            status = h[pid].get('status', {})
            if status.get('status_str') == 'error':
                msgs = status.get('messages', [])
                for m in msgs:
                    if m[0] == 'execution_error':
                        print(f"ERROR at node {m[1].get('node_id')}: {m[1].get('exception_message','')[:500]}")
                break
            elif status.get('completed'):
                print('DONE!')
                outputs = h[pid].get('outputs', {})
                for k, v in outputs.items():
                    print(f"  Node {k}: {list(v.keys()) if isinstance(v, dict) else v}")
                break
    except:
        pass
    time.sleep(10)
    if i % 3 == 0:
        print(f'  [{i}] still running...')
else:
    print('TIMEOUT after 30 min')
