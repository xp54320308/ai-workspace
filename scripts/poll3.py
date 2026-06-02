import json, urllib.request, time
pid = "df353700-f4f2-48d2-baae-1a7a7c3020a0"
print(f"Polling {pid}...")
for i in range(240):
    time.sleep(10)
    try:
        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}").read())
        if pid in h:
            s = h[pid].get("status", {})
            if s.get("completed"):
                print("COMPLETED!")
                for nid, out in h[pid].get("outputs", {}).items():
                    for g in out.get("gifs", []):
                        print(f"  Video: {g.get('filename', '?')}")
                break
            elif s.get("status_str") == "error":
                print("ERROR!")
                for m in s.get("messages", []):
                    print(f"  {m}")
                break
            else:
                if i % 3 == 0: print(f"Running... {i*10}s")
    except Exception:
        if i % 6 == 0: print(f"Polling... {i*10}s")
else:
    print("Timeout")
