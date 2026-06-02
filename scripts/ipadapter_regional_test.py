"""
IP-Adapter Regional 2-Character Test Script
用法: python ipadapter_regional_test.py --char_a path/to/A.png --char_b path/to/B.png
"""
import json
import argparse
import urllib.request
import urllib.parse
import time
import os

COMFYUI_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "..", "workflows", "ipadapter_regional_2chars.json")

def load_workflow():
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def upload_image(filepath):
    """Upload image to ComfyUI input directory"""
    import mimetypes
    filename = os.path.basename(filepath)
    mime_type = mimetypes.guess_type(filepath)[0] or "image/png"
    
    with open(filepath, "rb") as f:
        image_data = f.read()
    
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()
    
    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"  Uploaded: {filename} → {result}")
    return result.get("name", filename)

def queue_prompt(workflow):
    """Submit workflow to ComfyUI queue"""
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result.get("prompt_id")

def check_status(prompt_id):
    """Check if generation is done"""
    resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
    history = json.loads(resp.read())
    return prompt_id in history

def main():
    parser = argparse.ArgumentParser(description="IP-Adapter Regional 2-Character Test")
    parser.add_argument("--char_a", required=True, help="Character A image path")
    parser.add_argument("--char_b", required=True, help="Character B image path")
    parser.add_argument("--prompt_a", default="a beautiful woman with black hair, wearing a white dress, standing on the left side",
                        help="Character A prompt")
    parser.add_argument("--prompt_b", default="a handsome man with brown hair, wearing a black jacket, standing on the right side",
                        help="Character B prompt")
    parser.add_argument("--scene", default="two people standing together in a park, sunny day, detailed, high quality, 8k",
                        help="Scene/global prompt")
    parser.add_argument("--checkpoint", default="sd_xl_base_1.0.safetensors",
                        help="SDXL checkpoint filename")
    parser.add_argument("--weight", type=float, default=0.8, help="IP-Adapter image weight")
    parser.add_argument("--steps", type=int, default=30, help="Sampling steps")
    parser.add_argument("--cfg", type=float, default=7.0, help="CFG scale")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--width", type=int, default=1024, help="Output width")
    parser.add_argument("--height", type=int, default=1024, help="Output height")
    args = parser.parse_args()

    print("=== IP-Adapter Regional 2-Character Test ===")
    
    # Upload images
    print("\n[1/5] Uploading images...")
    char_a_name = upload_image(args.char_a)
    char_b_name = upload_image(args.char_b)
    
    # Load and configure workflow
    print("\n[2/5] Configuring workflow...")
    wf = load_workflow()
    
    # Node 1: Checkpoint
    wf["1"]["widgets_values"][0] = args.checkpoint
    # Node 2: Character A image
    wf["2"]["widgets_values"][0] = char_a_name
    # Node 3: Character B image
    wf["3"]["widgets_values"][0] = char_b_name
    # Node 6: Character A prompt
    wf["6"]["widgets_values"][0] = args.prompt_a
    # Node 7: Character B prompt
    wf["7"]["widgets_values"][0] = args.prompt_b
    # Node 8: Scene prompt
    wf["8"]["widgets_values"][0] = args.scene
    # Node 10: IP-Adapter weight for A
    wf["10"]["widgets_values"][0] = args.weight
    # Node 11: IP-Adapter weight for B
    wf["11"]["widgets_values"][0] = args.weight
    # Node 17: Latent size
    wf["17"]["widgets_values"] = [args.width, args.height, 1]
    # Node 18: KSampler
    wf["18"]["widgets_values"][0] = args.seed
    wf["18"]["widgets_values"][2] = args.steps
    wf["18"]["widgets_values"][3] = args.cfg
    
    # Queue
    print("\n[3/5] Queuing generation...")
    prompt_id = queue_prompt(wf)
    print(f"  Prompt ID: {prompt_id}")
    
    # Wait
    print("\n[4/5] Waiting for completion...")
    while not check_status(prompt_id):
        time.sleep(2)
        print(".", end="", flush=True)
    print("\n  Done!")
    
    # Result
    print("\n[5/5] Checking output...")
    resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}")
    history = json.loads(resp.read())
    if prompt_id in history:
        outputs = history[prompt_id].get("outputs", {})
        for node_id, output in outputs.items():
            if "images" in output:
                for img in output["images"]:
                    print(f"  Output: {img.get('filename', 'unknown')}")
    
    print("\n=== Complete ===")

if __name__ == "__main__":
    main()
