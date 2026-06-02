# Spring Video Pipeline - 9 segments, 1 minute total
# Each segment: 5s, ~99 frames @ 24fps

$comfyui = "http://127.0.0.1:8188"
$outputDir = "F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
$inputDir = "F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

$segments = @(
    @{Num=1; Prefix="spring_seg01"; Seed=100001; Text="a beautiful anime girl sitting quietly by a window, warm golden sunlight streaming through sheer white curtains gently blowing in the breeze, she looks out the window peacefully, soft ambient light, dust particles floating in sunbeams, cozy room interior, cinematic warm tones, 4k quality"; Image="01_wind_hand_cheek_start.png"}
    @{Num=2; Prefix="spring_seg02"; Seed=100002; Text="the girl slowly stands up from sitting, she turns gracefully toward the window, sunlight illuminating her face, her hair swaying with the movement, warm golden lighting, gentle motion, cinematic, 4k quality"; Image="FROM_PREV"}
    @{Num=3; Prefix="spring_seg03"; Seed=100003; Text="the girl pushes open a wooden door and steps outside into a beautiful garden, bright daylight floods in, cherry blossom trees visible in the background, she walks through the doorway with determination, fresh spring breeze, cinematic transition from indoor to outdoor, 4k quality"; Image="FROM_PREV"}
    @{Num=4; Prefix="spring_seg04"; Seed=100004; Text="the girl walks along a stone path through a cherry blossom garden, pink petals floating gently around her, sunlight filtering through the trees creating dappled light patterns on the ground, her dress swaying with each step, beautiful spring scenery, cinematic tracking shot, 4k quality"; Image="FROM_PREV"}
    @{Num=5; Prefix="spring_seg05"; Seed=100005; Text="the girl stops walking and reaches out gently to touch a cherry blossom branch, she brings her face closer to smell the flowers, petals falling softly around her fingers, close up shot with bokeh background, warm sunlight, delicate motion, 4k quality"; Image="FROM_PREV"}
    @{Num=6; Prefix="spring_seg06"; Seed=100006; Text="a sudden gust of wind blows through the cherry blossom trees, hundreds of pink petals swirl and dance through the air around the girl, her hair and dress billowing in the wind, she looks up in wonder at the petal storm, dramatic lighting, magical spring moment, 4k quality"; Image="FROM_PREV"}
    @{Num=7; Prefix="spring_seg07"; Seed=100007; Text="the girl turns her head back toward the camera and smiles warmly, a gentle soft smile full of joy, petals still floating around her, golden hour sunlight creating a warm glow on her face, shallow depth of field, cinematic portrait shot, 4k quality"; Image="FROM_PREV"}
    @{Num=8; Prefix="spring_seg08"; Seed=100008; Text="the girl starts running playfully through the cherry blossom grove, her dress flowing and bouncing with each step, she runs along the path with joy and energy, cherry trees passing by on both sides, dynamic camera following her movement, spring afternoon light, 4k quality"; Image="FROM_PREV"}
    @{Num=9; Prefix="spring_seg09"; Seed=100009; Text="the girl walks away from camera into the distance along a beautiful tree-lined path, sunset golden hour light, her silhouette growing smaller, cherry blossom petals falling gently, the scene slowly fading to warm orange sunset tones, peaceful ending, cinematic long shot, 4k quality"; Image="FROM_PREV"}
)

function Submit-Segment($seg) {
    $imageName = $seg.Image
    if ($imageName -eq "FROM_PREV") {
        $prevNum = $seg.Num - 1
        $prevPrefix = "spring_seg{0:D2}" -f $prevNum
        $prevLastFrame = "$outputDir\${prevPrefix}_00099_.png"
        $imageName = "spring_seg{0:D2}_start.png" -f $seg.Num
        Copy-Item $prevLastFrame "$inputDir\$imageName" -Force
        Write-Host "  首帧 <- ${prevPrefix} 尾帧"
    }

    $workflow = @{
        "3" = @{ "class_type" = "LoadFramePackModel"; "inputs" = @{ "model" = "FramePackI2V_HY_fp8_e4m3fn.safetensors"; "base_precision" = "bf16"; "quantization" = "fp8_e4m3fn"; "load_device" = "offload_device" } }
        "4" = @{ "class_type" = "DualCLIPLoader"; "inputs" = @{ "clip_name1" = "clip_l.safetensors"; "clip_name2" = "llava_llama3_fp8_scaled.safetensors"; "type" = "hunyuan_video" } }
        "5" = @{ "class_type" = "CLIPVisionLoader"; "inputs" = @{ "clip_name" = "sigclip_vision_patch14_384.safetensors" } }
        "6" = @{ "class_type" = "VAELoader"; "inputs" = @{ "vae_name" = "hunyuan_video_vae_bf16.safetensors" } }
        "7" = @{ "class_type" = "LoadImage"; "inputs" = @{ "image" = $imageName } }
        "8" = @{ "class_type" = "CLIPTextEncode"; "inputs" = @{ "text" = $seg.Text; "clip" = @("4", 0) } }
        "9" = @{ "class_type" = "ConditioningZeroOut"; "inputs" = @{ "conditioning" = @("8", 0) } }
        "10" = @{ "class_type" = "CLIPVisionEncode"; "inputs" = @{ "clip_vision" = @("5", 0); "image" = @("7", 0); "crop" = "center" } }
        "11" = @{ "class_type" = "VAEEncode"; "inputs" = @{ "pixels" = @("7", 0); "vae" = @("6", 0) } }
        "12" = @{ "class_type" = "FramePackSampler"; "inputs" = @{ "model" = @("3", 0); "positive" = @("8", 0); "negative" = @("9", 0); "start_latent" = @("11", 0); "image_embeds" = @("10", 0); "steps" = 30; "use_teacache" = $true; "teacache_rel_l1_thresh" = 0.12; "cfg" = 1.0; "guidance_scale" = 14.0; "shift" = 0.0; "seed" = $seg.Seed; "latent_window_size" = 9; "total_second_length" = 5.0; "gpu_memory_preservation" = 6.0; "sampler" = "unipc_bh2" } }
        "13" = @{ "class_type" = "VAEDecodeTiled"; "inputs" = @{ "samples" = @("12", 0); "vae" = @("6", 0); "tile_size" = 256; "temporal_size" = 64; "overlap" = 64; "temporal_overlap" = 8 } }
        "14" = @{ "class_type" = "SaveImage"; "inputs" = @{ "images" = @("13", 0); "filename_prefix" = $seg.Prefix } }
    }

    $body = @{ prompt = $workflow } | ConvertTo-Json -Depth 15
    $resp = Invoke-RestMethod -Uri "$comfyui/prompt" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    return $resp.prompt_id
}

function Wait-Completion($PromptId, $SegName, $Timeout = 600) {
    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        Start-Sleep -Seconds 30
        $elapsed += 30
        try {
            $history = Invoke-RestMethod -Uri "$comfyui/history/$PromptId" -TimeoutSec 5
            $entry = $history.PSObject.Properties.Value
            if ($entry.status.completed) {
                $count = $entry.outputs."14".images.Count
                Write-Host "  ✅ $SegName 完成 (${elapsed}s, ${count}帧)"
                return $true
            } elseif ($entry.status.status_str -eq "error") {
                $msg = ($entry.status.messages | Where-Object { $_[0] -eq "execution_error" })[1].exception_message
                Write-Host "  ❌ $SegName 失败: $msg"
                return $false
            }
        } catch {}
        Write-Host "  ⏳ $SegName ${elapsed}s..."
    }
    Write-Host "  ⏰ $SegName 超时"
    return $false
}

# Main pipeline
Write-Host "🎬 春日漫步 - 1分钟短片制作开始"
Write-Host "================================"

$startTime = Get-Date
$videoFiles = @()

foreach ($seg in $segments) {
    $segName = "第$($seg.Num)段: $($seg.Prefix)"
    Write-Host "`n--- $segName ---"
    
    $promptId = Submit-Segment $seg
    Write-Host "  提交: $promptId"
    
    $ok = Wait-Completion $promptId $segName
    if (-not $ok) {
        Write-Host "  ⚠️ 跳过此段"
        continue
    }
    
    # Convert frames to MP4
    $videoPath = "$outputDir\$($seg.Prefix)_24fps.mp4"
    $framePattern = "$outputDir\$($seg.Prefix)_%05d_.png"
    & "F:\Comfyui\ComfyUI-aki-v3\python\python.exe" -c "
import subprocess
cmd = ['ffmpeg','-y','-framerate','24','-i','$framePattern','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-preset','medium','$videoPath']
subprocess.run(cmd, capture_output=True)
" 2>$null
    $videoFiles += $videoPath
    Write-Host "  视频: $videoPath"
}

# Combine all segments with crossfade transitions
Write-Host "`n================================"
Write-Host "🎞️ 拼接视频（交叉淡入淡出转场）"

$combinedPath = "$outputDir\spring_walk_1min_final.mp4"

# Build ffmpeg filter for crossfade transitions
$inputs = ""
$filterParts = @()
$crossfadeDuration = 0.5  # 0.5 second crossfade

for ($i = 0; $i -lt $videoFiles.Count; $i++) {
    $inputs += " -i `"$($videoFiles[$i])`""
}

# Build xfade filter chain
if ($videoFiles.Count -eq 1) {
    $filter = ""
} else {
    $chain = @()
    $prevLabel = "[0:v]"
    $offset = 5.0 - $crossfadeDuration  # offset = segment duration - crossfade
    
    for ($i = 1; $i -lt $videoFiles.Count; $i++) {
        $outLabel = if ($i -eq $videoFiles.Count - 1) { "[outv]" } else { "[v$i]" }
        $currentOffset = $offset * $i
        $chain += "$prevLabel[$i:v]xfade=transition=fade:duration=$crossfadeDuration:offset=$currentOffset$outLabel"
        $prevLabel = $outLabel
    }
    
    $filter = "-filter_complex `"$($chain -join ';')`" -map `"[outv]`""
}

$ffmpegCmd = "ffmpeg -y$inputs $filter -c:v libx64 -pix_fmt yuv420p -crf 17 -preset medium `"$combinedPath`""
# Use simpler concat with crossfade
Write-Host "  使用 concat + 淡入淡出..."

# Create concat list
$concatFile = "$outputDir\spring_concat.txt"
$videoFiles | ForEach-Object { "file '$_'" } | Set-Content $concatFile

# Simple concat first, then we'll add transitions
& "F:\Comfyui\ComfyUI-aki-v3\python\python.exe" -c @"
import subprocess, os

output_dir = r'$outputDir'
videos = [$(("'" + ($videoFiles -join "','") + "'"))]

if len(videos) == 1:
    os.rename(videos[0], r'$combinedPath')
else:
    # Concat with crossfade using ffmpeg xfade filter
    # For smooth transitions, use xfade between each pair
    n = len(videos)
    inputs = []
    for v in videos:
        inputs.extend(['-i', v])
    
    if n <= 1:
        filter_str = ''
    else:
        parts = []
        prev = '[0:v]'
        offset = 4.5  # 5s - 0.5s crossfade
        for i in range(1, n):
            out = '[outv]' if i == n-1 else f'[v{i}]'
            parts.append(f'{prev}[{i}:v]xfade=transition=fade:duration=0.5:offset={offset*i}{out}')
            prev = out
        filter_str = f'-filter_complex "{";".join(parts)}" -map "[outv]"'
    
    cmd = ['ffmpeg', '-y'] + inputs + filter_str.split() + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', r'$combinedPath']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        size = os.path.getsize(r'$combinedPath')
        print(f'✅ 最终视频: {size/1024/1024:.1f} MB')
    else:
        print(f'FFmpeg error: {result.stderr[-500:]}')
        # Fallback: simple concat
        concat_file = os.path.join(output_dir, 'concat_final.txt')
        with open(concat_file, 'w') as f:
            for v in videos:
                f.write(f"file '{v}'\n")
        cmd2 = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', r'$combinedPath']
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        if result2.returncode == 0:
            size = os.path.getsize(r'$combinedPath')
            print(f'✅ 最终视频(concat): {size/1024/1024:.1f} MB')
        else:
            print(f'Fallback error: {result2.stderr[-300:]}')
"@