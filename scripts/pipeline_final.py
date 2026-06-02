import subprocess, os, shutil, sys

WORKSPACE = r'C:\Users\qw\.openclaw\workspace\pipeline_test'
final = os.path.join(WORKSPACE, 'final_output.mp4')
video_webp = os.path.join(WORKSPACE, 'pipeline_video_00001_.webp')
video_mp4 = os.path.join(WORKSPACE, 'video.mp4')
audio_path = os.path.join(WORKSPACE, 'narration.mp3')

# Find ffmpeg
FFMPEG = None
for p in [r'C:\ffmpeg\bin\ffmpeg.exe', r'C:\Program Files\ffmpeg\bin\ffmpeg.exe', r'F:\ffmpeg\bin\ffmpeg.exe', r'C:\Users\qw\scoop\apps\ffmpeg\current\bin\ffmpeg.exe', shutil.which('ffmpeg')]:
    if p and os.path.exists(p):
        FFMPEG = p
        break

# Also check in common package managers
if not FFMPEG:
    import glob
    for pattern in [r'C:\Users\qw\scoop\*\ffmpeg.exe', r'C:\Users\qw\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe', r'C:\ProgramData\chocolatey\bin\ffmpeg.exe']:
        matches = glob.glob(pattern)
        if matches:
            FFMPEG = matches[0]
            break

if not FFMPEG:
    # Check ComfyUI python environment
    comfy_python = r'F:\Comfyui\ComfyUI-aki-v3\python'
    for root, dirs, files in os.walk(comfy_python):
        if 'ffmpeg.exe' in files:
            FFMPEG = os.path.join(root, 'ffmpeg.exe')
            break

if not FFMPEG:
    print("FFmpeg NOT FOUND! Please install ffmpeg.", flush=True)
    print("Attempting to use imageio instead...", flush=True)
    
    # Fallback: use imageio to create mp4 from webp
    try:
        import imageio.v3 as iio
        frames = iio.imread(video_webp, index=None)
        iio.imwrite(video_mp4, frames, fps=8)
        print(f"imageio OK: {video_mp4}", flush=True)
    except ImportError:
        print("imageio not available either.", flush=True)
        # Try pip install
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'imageio', '-q'], capture_output=True, timeout=30)
        import imageio.v3 as iio
        frames = iio.imread(video_webp, index=None)
        iio.imwrite(video_mp4, frames, fps=8)
        print(f"imageio (installed) OK: {video_mp4}", flush=True)
else:
    print(f"Found ffmpeg: {FFMPEG}", flush=True)
    # webp -> mp4
    r = subprocess.run([FFMPEG, '-y', '-i', video_webp, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', video_mp4], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"Error: {r.stderr[:300]}", flush=True)
    else:
        print(f"mp4 OK: {os.path.getsize(video_mp4)/1024/1024:.1f}MB", flush=True)

# TTS
print("=== TTS ===", flush=True)
text = "A beautiful sunset over the ocean. Golden light reflects on gentle waves as a sailing boat glides across the horizon."
try:
    import edge_tts, asyncio
    async def gen():
        c = edge_tts.Communicate(text, "en-US-AriaNeural")
        await c.save(audio_path)
    asyncio.run(gen())
    print(f"TTS OK: {os.path.getsize(audio_path)/1024:.0f}KB", flush=True)
except Exception as e:
    print(f"TTS error: {e}", flush=True)
    audio_path = None

# Merge
if os.path.exists(video_mp4) and audio_path and os.path.exists(audio_path) and FFMPEG:
    print("=== Merge ===", flush=True)
    r = subprocess.run([FFMPEG, '-y', '-i', video_mp4, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', final], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        shutil.copy2(video_mp4, final)
    else:
        print("Merge OK", flush=True)
elif os.path.exists(video_mp4):
    shutil.copy2(video_mp4, final)

if os.path.exists(final):
    print(f"\n✅ FINAL: {final} ({os.path.getsize(final)/1024/1024:.1f}MB)", flush=True)
else:
    print("FAILED", flush=True)
