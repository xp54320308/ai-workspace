#!/usr/bin/env python3
"""FramePack I2V v2 - improved quality"""
import json, urllib.request, uuid, time

workflow = {
    "1": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "llava_llama3_fp8_scaled.safetensors", "type": "hunyuan_video"}},
    "2": {"class_type": "LoadFramePackModel", "inputs": {"model": "FramePackI2V_HY_fp8_e4m3fn.safetensors", "base_precision": "bf16", "quantization": "fp8_e4m3fn", "load_device": "main_device"}},
    "3": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "4": {"class_type": "LoadImage", "inputs": {"image": "test_spring.jpg"}},
    "5": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["3", 0], "image": ["4", 0], "crop": "center"}},
    "6": {"class_type": "TextEncodeHunyuanVideo_ImageToVideo", "inputs": {"clip": ["1", 0], "clip_vision_output": ["5", 0], "prompt": "A beautiful woman in traditional Chinese hanfu standing gracefully in a courtyard, golden hour sunlight, silk fabric gently flowing in the breeze, cinematic lighting, shallow depth of field, 4K ultra detailed", "image_interleave": 2}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 0], "text": "blurry, distorted, low quality, watermark, text, deformed face, ugly"}},
    "8": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 768, "height": 512, "length": 33, "batch_size": 1}},
    "9": {"class_type": "FramePackSampler", "inputs": {"model": ["2", 0], "positive": ["6", 0], "negative": ["7", 0], "start_latent": ["8", 0], "steps": 30, "use_teacache": True, "teacache_rel_l1_thresh": 0.15, "cfg": 1.0, "guidance_scale": 10.0, "shift": 0.0, "seed": 12345, "latent_window_size": 9, "total_second_length": 5.0, "gpu_memory_preservation": 4.0, "sampler": "unipc_bh1"}},
    "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["11", 0]}},
    "11": {"class_type": "VAELoader", "inputs": {"vae_name": "hunyuan_video_vae_bf16.safetensors"}},
    "12": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["10", 0], "frame_rate": 16.0, "loop_count": 0, "filename_prefix": "framepack_hanfu_v2", "format": "video/h264-mp4", "pingpong": False, "save_output": True}}
}

payload = json.dumps({"prompt": workflow}).encode()
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=payload, headers={"Content-Type": "application/json"})

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    prompt_id = result.get("prompt_id")
    print(f"Submitted v2! Prompt ID: {prompt_id}")

    for i in range(180):
        time.sleep(10)
        try:
            h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{prompt_id}").read())
            if prompt_id in h:
                s = h[prompt_id].get("status", {})
                if s.get("completed"):
                    print("COMPLETED!")
                    for nid, out in h[prompt_id].get("outputs", {}).items():
                        for g in out.get("gifs", []):
                            print(f"  Video: {g.get('filename', '?')}")
                    break
                elif s.get("status_str") == "error":
                    print("ERROR!")
                    for m in s.get("messages", []):
                        print(f"  {m}")
                    break
                else:
                    if i % 3 == 0:
                        print(f"Running... {i*10}s")
        except Exception:
            if i % 6 == 0:
                print(f"Polling... {i*10}s")
    else:
        print("Timeout")
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode()}")
