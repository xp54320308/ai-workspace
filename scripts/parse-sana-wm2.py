with open(r"G:\AI\Sana\inference_video_scripts\inference_sana_wm.py", "r", encoding="utf-8") as f:
    content = f.read()

start = content.index("def _build_parser()")
end = content.index("def _resolve_trajectory")
section = content[start:end]
print(section)
