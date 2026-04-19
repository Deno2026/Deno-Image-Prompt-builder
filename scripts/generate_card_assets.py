from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image


DEFAULT_COMFY_BASE = "http://127.0.0.1:8188"
DEFAULT_WORKFLOW = Path(
    r"D:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\ComfyUI\user\default\workflows\GPT Image generate.json"
)
DEFAULT_COMFY_ROOT = Path(r"D:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\ComfyUI")
DEFAULT_MANIFEST = Path(__file__).with_name("comfy_card_manifest.v1.json")
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = DEFAULT_COMFY_ROOT / "output"
ASSET_DIR = REPO_ROOT / "assets" / "cards"

SUBJECT_PROMPT_BASES = {
    "subjects": "clean category cover image for a prompt builder app, premium square thumbnail, simple readable subject-first visual",
    "thumbnail-person": "beautiful korean woman, youtube thumbnail portrait, clear face, strong subject separation, clickable visual, photorealistic, square frame",
    "portrait": "beautiful elegant woman portrait, editorial photography, flattering skin texture, refined light, photorealistic, square frame",
    "selfie-sns": "beautiful korean woman selfie, stylish sns look, soft flattering light, photorealistic, square frame",
    "group-family": "photorealistic lifestyle couple or group portrait, attractive natural people, warm emotional tone, square frame",
    "fashion-beauty": "beautiful fashion model, premium editorial beauty photography, clean high-end styling, photorealistic, square frame",
    "profile-id": "professional beautiful woman profile photo, trustworthy polished expression, clean commercial portrait, photorealistic, square frame",
    "product": "premium commercial product photography, clean studio lighting, object-only composition, no people, photorealistic, square frame",
    "food-drink": "premium food photography, delicious editorial plating, object-only composition, no people, photorealistic, square frame",
    "landscape": "cinematic landscape photography, wide environmental storytelling, no people unless specified, photorealistic, square frame",
    "travel": "cinematic travel photography, destination atmosphere, low-clutter scene, no people unless specified, photorealistic, square frame",
    "service": "clean service branding visual, polished app or web campaign image, no people unless specified, photorealistic, square frame",
    "poster": "clean campaign poster visual, premium graphic-led composition, no people unless specified, photorealistic, square frame",
    "space": "premium interior photography, clean architectural space, no people, photorealistic, square frame",
    "architecture": "architectural exterior photography, clean facade composition, no people unless specified, photorealistic, square frame",
    "vehicle": "premium automotive photography, vehicle-only composition, no people unless specified, photorealistic, square frame",
    "animal": "wildlife or pet photography, subject-focused clean scene, no people, photorealistic, square frame",
    "workspace": "clean office or desk scene photography, no people unless specified, photorealistic, square frame",
    "fantasy": "cinematic fantasy concept art, environment-led dramatic scene, no people unless specified, highly detailed, square frame",
    "illustration": "clean character or illustration card art, polished stylized rendering, no people unless specified, highly detailed, square frame",
    "event": "event photography, clean documentary scene, no people unless specified, photorealistic, square frame",
    "broll": "clean cinematic b-roll frame, environment-led storytelling, no people unless specified, photorealistic, square frame",
}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.load(response)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def node_by_type(workflow: dict, node_type: str) -> dict:
    for node in workflow["nodes"]:
        if node["type"] == node_type:
            return node
    raise KeyError(f"Missing node type: {node_type}")


def extract_settings(workflow: dict) -> dict:
    clip = node_by_type(workflow, "CLIPLoader")
    vae = node_by_type(workflow, "VAELoader")
    unet = node_by_type(workflow, "UNETLoader")
    text = node_by_type(workflow, "CLIPTextEncode")
    save = node_by_type(workflow, "SaveImage")
    resize = node_by_type(workflow, "DenoResolutionSetup")
    latent = node_by_type(workflow, "EmptySD3LatentImage")
    sampler = node_by_type(workflow, "KSampler")
    model_sampling = node_by_type(workflow, "ModelSamplingAuraFlow")
    power_lora = node_by_type(workflow, "Power Lora Loader (rgthree)")

    loras = []
    for item in power_lora.get("widgets_values", []):
        if isinstance(item, dict) and {"on", "lora", "strength"}.issubset(item.keys()):
            clean = {
                "on": bool(item["on"]),
                "lora": item["lora"],
                "strength": float(item["strength"]),
            }
            if item.get("strengthTwo") is not None:
                clean["strengthTwo"] = float(item["strengthTwo"])
            loras.append(clean)

    return {
        "ids": {
            "clip": str(clip["id"]),
            "vae": str(vae["id"]),
            "unet": str(unet["id"]),
            "text": str(text["id"]),
            "save": str(save["id"]),
            "resize": str(resize["id"]),
            "latent": str(latent["id"]),
            "sampler": str(sampler["id"]),
            "model_sampling": str(model_sampling["id"]),
            "power_lora": str(power_lora["id"]),
            "conditioning_zero": "64",
            "decode": "65",
        },
        "clip": {
            "clip_name": clip["widgets_values"][0],
            "type": clip["widgets_values"][1],
            "device": clip["widgets_values"][2],
        },
        "vae": {"vae_name": vae["widgets_values"][0]},
        "unet": {
            "unet_name": unet["widgets_values"][0],
            "weight_dtype": unet["widgets_values"][1],
        },
        "text": {"default_prompt": text["widgets_values"][0]},
        "save": {"default_prefix": save["widgets_values"][0]},
        "resize": {
            "mode": resize["widgets_values"][0],
            "ratio_preset": resize["widgets_values"][1],
            "megapixels": resize["widgets_values"][2],
            "width": resize["widgets_values"][3],
            "height": resize["widgets_values"][4],
            "divisible_by": resize["widgets_values"][5],
            "resize_method": resize["widgets_values"][6],
            "interpolation": resize["widgets_values"][7],
        },
        "latent": {
            "width": latent["widgets_values"][0],
            "height": latent["widgets_values"][1],
            "batch_size": latent["widgets_values"][2],
        },
        "sampler": {
            "steps": sampler["widgets_values"][2],
            "cfg": sampler["widgets_values"][3],
            "sampler_name": sampler["widgets_values"][4],
            "scheduler": sampler["widgets_values"][5],
            "denoise": sampler["widgets_values"][6],
        },
        "model_sampling": {"shift": model_sampling["widgets_values"][0]},
        "power_loras": loras,
    }


def build_prompt_graph(settings: dict, prompt_text: str, filename_prefix: str, seed: int) -> dict:
    ids = settings["ids"]
    graph = {
        ids["clip"]: {
            "class_type": "CLIPLoader",
            "inputs": settings["clip"],
        },
        ids["vae"]: {
            "class_type": "VAELoader",
            "inputs": settings["vae"],
        },
        ids["unet"]: {
            "class_type": "UNETLoader",
            "inputs": settings["unet"],
        },
        ids["power_lora"]: {
            "class_type": "Power Lora Loader (rgthree)",
            "inputs": {
                "model": [ids["unet"], 0],
            },
        },
        ids["model_sampling"]: {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {
                "model": [ids["power_lora"], 0],
                "shift": settings["model_sampling"]["shift"],
            },
        },
        ids["text"]: {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": [ids["clip"], 0],
            },
        },
        ids["conditioning_zero"]: {
            "class_type": "ConditioningZeroOut",
            "inputs": {
                "conditioning": [ids["text"], 0],
            },
        },
        ids["latent"]: {
            "class_type": "EmptySD3LatentImage",
            "inputs": settings["latent"],
        },
        ids["sampler"]: {
            "class_type": "KSampler",
            "inputs": {
                "model": [ids["model_sampling"], 0],
                "seed": seed,
                "steps": settings["sampler"]["steps"],
                "cfg": settings["sampler"]["cfg"],
                "sampler_name": settings["sampler"]["sampler_name"],
                "scheduler": settings["sampler"]["scheduler"],
                "positive": [ids["text"], 0],
                "negative": [ids["conditioning_zero"], 0],
                "latent_image": [ids["latent"], 0],
                "denoise": settings["sampler"]["denoise"],
            },
        },
        ids["decode"]: {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": [ids["sampler"], 0],
                "vae": [ids["vae"], 0],
            },
        },
        ids["resize"]: {
            "class_type": "DenoResolutionSetup",
            "inputs": {
                "image": [ids["decode"], 0],
                "mode": settings["resize"]["mode"],
                "ratio_preset": settings["resize"]["ratio_preset"],
                "megapixels": settings["resize"]["megapixels"],
                "width": settings["resize"]["width"],
                "height": settings["resize"]["height"],
                "divisible_by": settings["resize"]["divisible_by"],
                "resize_method": settings["resize"]["resize_method"],
                "interpolation": settings["resize"]["interpolation"],
            },
        },
        ids["save"]: {
            "class_type": "SaveImage",
            "inputs": {
                "images": [ids["resize"], 0],
                "filename_prefix": filename_prefix,
            },
        },
    }

    for index, lora in enumerate(settings["power_loras"], start=1):
        graph[ids["power_lora"]]["inputs"][f"lora_{index}"] = lora

    return graph


def queue_prompt(comfy_base: str, graph: dict) -> str:
    payload = {"prompt": graph, "client_id": "prompt-builder-v2-batch"}
    response = post_json(f"{comfy_base}/prompt", payload)
    return response["prompt_id"]


def wait_for_completion(comfy_base: str, prompt_id: str, timeout_s: int = 600) -> dict:
    start = time.time()
    history_url = f"{comfy_base}/history/{urllib.parse.quote(prompt_id)}"
    while time.time() - start < timeout_s:
        data = get_json(history_url)
        if data and prompt_id in data:
            return data[prompt_id]
        time.sleep(1.5)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


def extract_output_image(history_item: dict, save_node_id: str) -> Path:
    outputs = history_item.get("outputs", {}).get(save_node_id, {})
    images = outputs.get("images", [])
    if not images:
        raise RuntimeError(f"No images found in history outputs for save node {save_node_id}")
    image = images[0]
    subfolder = image.get("subfolder", "")
    filename = image["filename"]
    return OUTPUT_DIR / subfolder / filename


def derive_prefix(subject: str, step: str, option_key: str) -> str:
    return f"prompt-builder-v2/{subject}/{step}/{option_key}"


def derive_asset_path(subject: str, step: str, option_key: str) -> Path:
    return ASSET_DIR / subject / step / f"{option_key}.webp"


def build_prompt_from_item(item: dict) -> str:
    if item.get("prompt"):
        return item["prompt"]

    subject = item["subject"]
    base = SUBJECT_PROMPT_BASES.get(subject, "photorealistic square card image")
    title = item.get("title", "").strip()
    cue = item.get("cue", "").strip()
    focus = ", ".join(part for part in [title, cue] if part)
    if focus:
        return f"{base}, {focus}"
    return base


def convert_to_webp(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.save(target, format="WEBP", quality=68, method=6)


def run_batch(args: argparse.Namespace) -> int:
    workflow = load_json(Path(args.workflow))
    manifest = load_json(Path(args.manifest))
    settings = extract_settings(workflow)

    items = manifest[: args.limit] if args.limit else manifest
    print(f"Loaded {len(items)} manifest items")

    for index, item in enumerate(items, start=1):
        subject = item["subject"]
        step = item["step"]
        option_key = item["option_key"]
        title = item.get("title", option_key)
        prompt_text = build_prompt_from_item(item)
        seed = random.randint(1, 2**32 - 1)
        prefix = derive_prefix(subject, step, option_key)
        asset_path = derive_asset_path(subject, step, option_key)

        print(f"[{index}/{len(items)}] {subject}/{step}/{option_key} :: {title}")
        if asset_path.exists() and not args.overwrite:
            print(f"  skip: {asset_path} already exists")
            continue
        print(f"  prompt: {prompt_text}")
        print(f"  prefix: {prefix}")

        graph = build_prompt_graph(settings, prompt_text, prefix, seed)
        prompt_id = queue_prompt(args.comfy_base, graph)
        history_item = wait_for_completion(args.comfy_base, prompt_id, timeout_s=args.timeout)
        output_image = extract_output_image(history_item, settings["ids"]["save"])

        if not output_image.exists():
            raise FileNotFoundError(f"ComfyUI reported output but file not found: {output_image}")

        convert_to_webp(output_image, asset_path)
        print(f"  saved: {asset_path}")

        if args.keep_png_copy:
            copy_path = asset_path.with_suffix(".png")
            shutil.copy2(output_image, copy_path)
            print(f"  png copy: {copy_path}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate prompt-builder card images through ComfyUI.")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--comfy-base", default=DEFAULT_COMFY_BASE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--keep-png-copy", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(run_batch(parse_args()))
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        raise SystemExit(130)
    except urllib.error.HTTPError as error:
        print(f"HTTP error: {error}", file=sys.stderr)
        if error.fp:
            print(error.fp.read().decode("utf-8", "ignore"), file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
