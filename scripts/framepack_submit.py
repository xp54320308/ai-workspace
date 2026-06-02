#!/usr/bin/env python3
"""FramePack I2V test - submit and poll"""
import json, urllib.request, uuid, time

workflow = {
    "1": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "llava_llama3_fp8_scaled.safetensors", "type": "hunyuan_video"}},
    "2": {"class_type": "LoadFramePackModel", "inputs": {"model": "FramePackI2V_HY_fp8_e4m3fn.safetensors", "base_precision": "bf16", "quantization": "fp8_e4m3fn", "load_device": "main_device"}},
    "3": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "4": {"class_type": "LoadImage", "inputs": {"image": "test_spring.jpg"}},
    "5": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["3", 0], "image": ["4", 0], "crop": "center"}},
    "6": {"class_type": "TextEncodeHunyuanVideo_ImageToVideo", "inputs": {"clip": ["1", 0], "clip_vision_output": ["5", 0], "prompt": "A beautiful spring scene, cherry blossoms swaying gently in the breeze, soft sunlight filtering through petals, peaceful walking path, cinematic quality, 4K", "image_interleave": 2}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 0], "text": "blurry, distorted, low quality, watermark, text"}},
    "8": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 512, "height": 320, "length": 33, "batch_size": 1}},
    "9": {"class_type": "FramePackSampler", "inputs": {"model": ["2", 0], "positive": ["6", 0], "negative": ["7", 0], "start_latent": ["8", 0], "steps": 25, "use_teacache": True, "teacache_rel_l1_thresh": 0.15, "cfg": 1.0, "guidance_scale": 10.0, "shift": 0.0, "seed": 42, "latent_window_size": 9, "total_second_length": 5.0, "gpu_memory_preservation": 6.0, "sampler": "unipc_bh1"}},
    "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["11", 0]}},
    "11": {"class_type": "VAELoader", "inputs": {"vae_name": "hunyuan_video_vae_bf16.safetensors"}},
    "12": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["10", 0], "frame_rate": 16.0, "loop_count": 0, "filename_prefix": "framepack_spring_test", "format": "video/h264-mp4", "pingpong": False, "save_output": True}}
}

payload = json.dumps({"prompt": workflow}).encode()
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=payload, headers={"Content-Type": "application/json"})

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    prompt_id = result.get("prompt_id")
    print(f"Submitted! Prompt ID: {prompt_id}")

    for i in range(120):
        time.sleep(5)
        try:
            h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{prompt_id}").read())
            if prompt_id in h:
                s = h[prompt_id].get("status", {})
                if s.get("completed"):
                    print("COMPLETED!")
                    for nid, out in h[prompt_id].get("outputs", {}).items():
                        for g in out.get("gifs", []):
                            fn = g.get("filename", "unknown")
                            print(f"  Video: {fn}")
                        for img in out.get("images", []):
                            fn = img.get("filename", "unknown")
                            print(f"  Image: {fn}")
                    break
                elif s.get("status_str") == "error":
                    print("ERROR!")
                    for m in s.get("messages", []):
                        print(f"  {m}")
                    break
                else:
                    if i % 6 == 0:
                        print(f"Running... {i*5}s elapsed")
        except Exception:
            if i % 6 == 0:
                print(f"Polling... {i*5}s")
    else:
        print("Timeout after 10 minutes")

except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP Error {e.code}: {body}")
except Exception as e:
    print(f"Error: {e}")
