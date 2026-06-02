import subprocess, os, shutil, sys

WORKSPACE = r'C:\Users\qw\.openclaw\workspace\pipeline_test'
final = os.path.join(WORKSPACE, 'final_output.mp4')
video_webp = os.path.join(WORKSPACE, 'pipeline_video_00001_.webp')
video_mp4 = os.path.join(WORKSPACE, 'video.mp4')
audio_path = os.path.join(WORKSPACE, 'narration.mp3')

# Step 1: TTS
print("=== TTS ===", flush=True)
text = "A beautiful sunset over the ocean. Golden light reflects on gentle waves as a sailing boat glides across the horizon."
try:
    import edge_tts, asyncio
    async def gen():
        c = edge_tts.Communicate(text, "en-US-AriaNeural")
        await c.save(audio_path)
    asyncio.run(gen())
    print(f"TTS OK: {audio_path} ({os.path.getsize(audio_path)/1024:.0f}KB)", flush=True)
except Exception as e:
    print(f"TTS failed: {e}", flush=True)
    audio_path = None

# Step 2: webp -> mp4
print("=== webp -> mp4 ===", flush=True)
r = subprocess.run(['ffmpeg', '-y', '-i', video_webp, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video_mp4], capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    print(f"webp->mp4 error: {r.stderr[:300]}", flush=True)
else:
    print(f"mp4 OK: {video_mp4} ({os.path.getsize(video_mp4)/1024/1024:.1f}MB)", flush=True)

# Step 3: merge audio
if audio_path and os.path.exists(audio_path) and os.path.exists(video_mp4):
    print("=== merge audio ===", flush=True)
    r = subprocess.run(['ffmpeg', '-y', '-i', video_mp4, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', final], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"merge error: {r.stderr[:300]}", flush=True)
        shutil.copy2(video_mp4, final)
    else:
        print(f"merge OK", flush=True)
else:
    shutil.copy2(video_mp4, final)

if os.path.exists(final):
    sz = os.path.getsize(final) / 1024 / 1024
    print(f"\n✅ FINAL: {final} ({sz:.1f}MB)", flush=True)
else:
    print("FAILED", flush=True)
