import os, subprocess, shutil, sys

WORKSPACE = r'C:\Users\qw\.openclaw\workspace\pipeline_test'
FFMPEG = r'F:\Comfyui\ComfyUI-aki-v3\python\ffmpeg.exe'
video_webp = os.path.join(WORKSPACE, 'pipeline_video_00001_.webp')
frames_dir = os.path.join(WORKSPACE, 'frames')
video_mp4 = os.path.join(WORKSPACE, 'video.mp4')
audio_path = os.path.join(WORKSPACE, 'narration.mp3')
final = os.path.join(WORKSPACE, 'final_output.mp4')

# Step 1: Extract frames from animated webp
os.makedirs(frames_dir, exist_ok=True)
print("Extracting frames from webp...", flush=True)
from PIL import Image
img = Image.open(video_webp)
frame_count = 0
try:
    while True:
        frame_path = os.path.join(frames_dir, f'frame_{frame_count:04d}.png')
        img.save(frame_path)
        frame_count += 1
        img.seek(img.tell() + 1)
except EOFError:
    pass
print(f"Extracted {frame_count} frames", flush=True)

# Step 2: Create video from frames
print("Creating mp4 from frames...", flush=True)
r = subprocess.run([FFMPEG, '-y', '-framerate', '8', '-i', os.path.join(frames_dir, 'frame_%04d.png'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', video_mp4], capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    print(f"Error: {r.stderr[:300]}", flush=True)
else:
    sz = os.path.getsize(video_mp4) / 1024 / 1024
    print(f"mp4 OK: {sz:.1f}MB", flush=True)

# Step 3: Merge audio
if os.path.exists(video_mp4) and os.path.exists(audio_path):
    print("Merging audio...", flush=True)
    r = subprocess.run([FFMPEG, '-y', '-i', video_mp4, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', final], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"Merge error: {r.stderr[:200]}", flush=True)
        shutil.copy2(video_mp4, final)
    else:
        print("Merge OK", flush=True)
else:
    if os.path.exists(video_mp4):
        shutil.copy2(video_mp4, final)

if os.path.exists(final):
    sz = os.path.getsize(final) / 1024 / 1024
    print(f"FINAL: {final} ({sz:.1f}MB)", flush=True)
else:
    print("FAILED", flush=True)

# Cleanup frames
shutil.rmtree(frames_dir, ignore_errors=True)
