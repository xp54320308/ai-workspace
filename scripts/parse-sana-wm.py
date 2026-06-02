import re

with open(r"G:\AI\Sana\inference_video_scripts\inference_sana_wm.py", "r", encoding="utf-8") as f:
    content = f.read()

# Extract the _build_parser function
start = content.index("def _build_parser()")
end = content.index("def _resolve_trajectory")
section = content[start:end]

# Find all add_argument lines
for line in section.split("\n"):
    if "add_argument" in line:
        print(line.strip())
