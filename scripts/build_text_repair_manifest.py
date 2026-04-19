from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_HTML = REPO_ROOT / "image.html"
ASSET_DIR = REPO_ROOT / "assets" / "cards"
DEFAULT_OUTPUT = Path(__file__).with_name("comfy_card_manifest.text_repair.auto.json")
DEFAULT_REPORT = Path(__file__).with_name("ocr_text_flag_report.json")


SUBJECT_PROMPT_BASES = {
    "subjects": "clean category preview image, premium square thumbnail, single-subject visual, no overlay text",
    "thumbnail-person": "beautiful korean woman, clickable portrait-led visual, clear face, strong subject separation, no overlay text, photorealistic, square frame",
    "portrait": "beautiful elegant woman portrait, editorial photography, flattering skin texture, refined light, photorealistic, square frame",
    "selfie-sns": "beautiful korean woman selfie, stylish sns look, soft flattering light, photorealistic, square frame",
    "group-family": "photorealistic lifestyle couple or group portrait, attractive natural people, warm emotional tone, square frame",
    "fashion-beauty": "beautiful fashion model, premium editorial beauty photography, clean high-end styling, photorealistic, square frame",
    "profile-id": "professional beautiful woman profile photo, trustworthy polished expression, clean commercial portrait, photorealistic, square frame",
    "product": "premium commercial product photography, clean studio lighting, object-only composition, no people, photorealistic, square frame",
    "food-drink": "premium food photography, delicious editorial plating, object-only composition, no people, photorealistic, square frame",
    "landscape": "cinematic landscape photography, wide environmental storytelling, no people unless specified, photorealistic, square frame",
    "travel": "cinematic travel photography, destination atmosphere, low-clutter scene, no people unless specified, photorealistic, square frame",
    "service": "clean digital service concept scene, polished brand-led visual, no readable screen text, no people unless specified, photorealistic, square frame",
    "poster": "clean graphic key visual, premium composition with blank copy space, no rendered typography, no people unless specified, photorealistic, square frame",
    "space": "premium interior photography, clean architectural space, no people, photorealistic, square frame",
    "architecture": "architectural exterior photography, clean facade composition, no people unless specified, photorealistic, square frame",
    "vehicle": "premium automotive photography, vehicle-only composition, no people unless specified, photorealistic, square frame",
    "animal": "wildlife or pet photography, subject-focused clean scene, no people, photorealistic, square frame",
    "workspace": "clean office or desk scene photography, blank or unreadable screens only, no people unless specified, photorealistic, square frame",
    "fantasy": "cinematic fantasy concept art, environment-led dramatic scene, no people unless specified, highly detailed, square frame",
    "illustration": "clean character or illustration card art, polished stylized rendering, no people unless specified, highly detailed, square frame",
    "event": "event photography, clean documentary scene, no people unless specified, photorealistic, square frame",
    "broll": "clean cinematic atmospheric frame, environment-led storytelling, no titles or captions, no people unless specified, photorealistic, square frame",
}

FORCE_REPAIR_SUBJECTS = {"broll"}

HIGH_RISK_SUBJECTS = {"service", "poster", "workspace", "broll", "subjects", "thumbnail-person"}
HIGH_RISK_STEPS = {"text", "layout", "subject"}

SPECIAL_OPTION_HINTS = {
    "thumb-text-left": "subject on the right, clear empty negative space on the left",
    "thumb-text-right": "subject on the left, clear empty negative space on the right",
    "thumb-text-top": "subject in the lower area, clear empty negative space at the top",
    "thumb-text-bottom": "subject in the upper area, clear empty negative space at the bottom",
    "thumb-text-center": "subject pushed slightly off-center with broad empty negative space",
    "thumb-text-badge": "clean thumbnail composition with a small empty badge area only",
    "poster-layout-center": "single dominant visual in the center with clean negative space around it",
    "poster-layout-top": "dominant lower visual with wide clean top area",
    "poster-layout-bottom": "dominant upper visual with wide clean lower area",
    "service-visual-ui": "device-led clean brand scene with blank and unreadable screen",
    "service-visual-people": "person using a service naturally, any device screen blank and unreadable",
    "service-visual-mix": "clean lifestyle brand scene, no readable UI or labels",
    "work-layout-monitor": "clean desk setup, monitor present but screen blank and unreadable",
    "work-layout-top": "desk scene with broad top negative space and no readable screen",
    "broll-use-intro": "clean intro-style establishing shot with no titles or overlays",
    "broll-use-outro": "clean ending shot with quiet negative space and no titles or overlays",
    "broll-use-empty": "minimal scene with broad clean empty space, no text or symbols",
}

SUBJECT_CARD_HINTS = {
    "thumbnail-person": "clickable portrait-led thumbnail visual with no lettering",
    "portrait": "single attractive portrait visual with no overlay text",
    "selfie-sns": "stylish selfie visual with no overlay text",
    "group-family": "warm duo or group portrait visual with no overlay text",
    "fashion-beauty": "high-end beauty or fashion visual with no overlay text",
    "profile-id": "trustworthy profile portrait visual with no overlay text",
    "product": "clean product visual with no brand labels or text",
    "food-drink": "delicious food visual with no menu text",
    "vehicle": "vehicle hero visual with no logo text",
    "space": "interior scene visual with no signage",
    "architecture": "architectural facade visual with no signage",
    "landscape": "cinematic landscape visual with no overlay text",
    "travel": "travel destination visual with no overlay text",
    "animal": "animal-focused visual with no overlay text",
    "workspace": "clean workspace visual with no readable screen text",
    "service": "clean service brand visual with no readable UI text",
    "poster": "graphic-led hero visual with no typography rendered",
    "fantasy": "fantasy concept visual with no overlay text",
    "illustration": "stylized illustration visual with no overlay text",
    "event": "event scene visual with no signage text",
    "broll": "clean b-roll visual with no titles or captions",
}

TOKEN_HINTS = {
    "left": "left-side empty space",
    "right": "right-side empty space",
    "top": "top empty space",
    "bottom": "bottom empty space",
    "center": "center-led composition",
    "wide": "broad open scene",
    "close": "tight close framing",
    "empty": "clean minimal negative space",
    "ui": "blank unreadable interface surface",
    "screen": "blank unreadable screen",
    "monitor": "blank unreadable monitor",
    "phone": "blank unreadable phone screen",
    "badge": "small accent area only",
    "hero": "single dominant hero visual",
    "layout": "clean layout-first composition",
    "text": "copy-free negative space",
    "poster": "graphic-led hero scene",
    "service": "service-led branding scene",
    "work": "clean desk environment",
    "broll": "clean atmospheric frame",
    "travel": "destination-led travel scene",
    "product": "unbranded product focus",
    "luxury": "luxury mood",
    "premium": "premium mood",
    "award": "award-stage moment",
    "booth": "brand booth scene",
    "lecture": "speaker-led lecture scene",
    "mix": "balanced crowd and stage scene",
    "main": "main keynote moment",
    "presentation": "presentation-led stage scene",
    "future": "cool futuristic mood",
    "festival": "festival energy scene",
    "texture": "texture-led visual",
    "angle": "angled product composition",
    "beauty": "beauty product styling",
    "bottle": "bottle-shaped product focus",
    "gloss": "glossy surface highlight",
    "set": "styled product set scene",
    "splash": "liquid splash product scene",
    "low": "low-angle composition",
    "medium": "balanced mid-distance composition",
    "pov": "point-of-view composition",
    "symmetry": "symmetrical front composition",
    "calm": "calm clean mood",
    "clean": "clean minimal mood",
    "warm": "warm inviting mood",
    "education": "modern learning desk scene",
    "health": "clean wellness or care scene",
    "hand": "hand interaction with service device",
    "bold": "confident trustworthy mood",
    "friendly": "friendly approachable mood",
    "soft": "soft gentle trustworthy mood",
    "editorial": "editorial interior mood",
    "vintage": "slightly vintage travel mood",
    "drink": "drink-focused food visual",
    "food": "food-focused visual",
}

STOP_TOKENS = {
    "thumb", "pose", "mood", "detail", "focus", "comp", "composition", "visual",
    "use", "bg", "people", "group", "profile", "event", "animal",
    "product", "service", "space", "travel", "subjects", "motif", "trust",
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_option_sets(text: str) -> dict[str, list[tuple[str, str, str]]]:
    option_sets: dict[str, list[tuple[str, str, str]]] = {}
    pattern = re.compile(
        r"const\s+(\w+)\s*=\s*createOptions\([^\[]*\[(.*?)\]\s*\);",
        re.S,
    )
    row_pattern = re.compile(
        r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*(?:,\s*"[^"]*")?\s*\]'
    )

    for match in pattern.finditer(text):
        name = match.group(1)
        body = match.group(2)
        option_sets[name] = row_pattern.findall(body)
    return option_sets


def parse_subject_options(text: str) -> list[tuple[str, str, str]]:
    match = re.search(r"const\s+SUBJECT_OPTIONS\s*=\s*createOptions\([^\[]*\[(.*?)\]\s*\);", text, re.S)
    if not match:
        return []
    row_pattern = re.compile(
        r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?\s*\]'
    )
    rows = []
    for row in row_pattern.findall(match.group(1)):
        rows.append((row[0], row[1], row[2]))
    return rows


def parse_flow_profiles(text: str) -> dict[str, list[tuple[str, str]]]:
    flow_match = re.search(r"const FLOW_PROFILES = \{(.*?)\n\s*\};", text, re.S)
    if not flow_match:
        raise RuntimeError("Could not find FLOW_PROFILES in image.html")

    flow_body = flow_match.group(1)
    subject_pattern = re.compile(r'(?:\"([^\"]+)\"|(\w+))\s*:\s*\[(.*?)\]\s*,', re.S)
    step_pattern = re.compile(r'makeStep\(\s*"([^"]+)".*?,\s*(\w+)\s*\)', re.S)

    subjects: dict[str, list[tuple[str, str]]] = {}
    for subject_match in subject_pattern.finditer(flow_body):
        subject = subject_match.group(1) or subject_match.group(2)
        body = subject_match.group(3)
        subjects[subject] = step_pattern.findall(body)
    return subjects


def build_metadata_map() -> dict[tuple[str, str, str], dict]:
    text = load_text(IMAGE_HTML)
    option_sets = parse_option_sets(text)
    flow_profiles = parse_flow_profiles(text)
    subject_options = parse_subject_options(text)

    metadata: dict[tuple[str, str, str], dict] = {}

    for option_key, title, cue in subject_options:
        metadata[("subjects", "subject", option_key)] = {
            "subject": "subjects",
            "step": "subject",
            "option_key": option_key,
            "title": title,
            "cue": cue,
        }

    for subject, steps in flow_profiles.items():
        if subject == "manual":
            continue
        for step, option_set in steps:
            for option_key, title, cue in option_sets.get(option_set, []):
                metadata[(subject, step, option_key)] = {
                    "subject": subject,
                    "step": step,
                    "option_key": option_key,
                    "title": title,
                    "cue": cue,
                }
    return metadata


def scan_for_text(min_confidence: float, min_length: int) -> list[dict]:
    ocr = RapidOCR()
    flagged: list[dict] = []
    for path in ASSET_DIR.rglob("*.webp"):
        try:
            result, _ = ocr(str(path))
        except Exception:
            continue
        if not result:
            continue

        hits = []
        for item in result:
            text = item[1].strip()
            confidence = float(item[2])
            if text and len(text) >= min_length and confidence >= min_confidence:
                hits.append({"text": text, "confidence": confidence})
        if not hits:
            continue

        parts = path.relative_to(ASSET_DIR).parts
        if len(parts) != 3:
            continue
        subject, step, filename = parts
        flagged.append(
            {
                "subject": subject,
                "step": step,
                "option_key": Path(filename).stem,
                "path": str(path),
                "hits": hits,
            }
        )
    return flagged


def build_semantic_hint(meta: dict) -> str:
    subject = meta["subject"]
    step = meta["step"]
    option_key = meta["option_key"]

    if subject == "subjects" and step == "subject":
        return SUBJECT_CARD_HINTS.get(option_key, "clean subject category visual with no lettering")

    if option_key in SPECIAL_OPTION_HINTS:
        return SPECIAL_OPTION_HINTS[option_key]

    parts = []
    for token in option_key.split("-"):
        if token in STOP_TOKENS:
            continue
        hint = TOKEN_HINTS.get(token)
        if hint and hint not in parts:
            parts.append(hint)

    if parts:
        return ", ".join(parts[:3])

    title = meta["title"].strip()
    cue = meta["cue"].strip()
    return ", ".join(part for part in [title, cue] if part)


def build_notext_prompt(meta: dict) -> str:
    subject = meta["subject"]
    step = meta["step"]
    option_key = meta["option_key"]
    base = SUBJECT_PROMPT_BASES.get(subject, "photorealistic square card image")
    title = meta["title"].strip()
    cue = meta["cue"].strip()

    no_text = (
        "image only, absolutely no text, no letters, no words, no typography, no logo, "
        "no watermark, no captions, no subtitles, no signage, no brand name, no visible symbols"
    )
    if subject in HIGH_RISK_SUBJECTS or step in HIGH_RISK_STEPS:
        no_text = (
            "image only, use clean empty negative space where copy could be added later, but do not render any text, "
            "letters, words, typography, logo, watermark, captions, subtitles, signage, brand names, symbols, or numbers"
        )
    elif subject in {"product", "vehicle", "food-drink"}:
        no_text = (
            "image only, unbranded and unlabeled, no package text, no menu text, no dashboard text, no logo, "
            "no watermark, no captions, no signage, no visible symbols or numbers"
        )

    if subject in {"service", "workspace"}:
        no_text += ", if a device screen appears keep it blank, dark, or unreadable"

    focus = build_semantic_hint(meta)
    if not focus:
        focus = ", ".join(part for part in [title, cue] if part)
    return f"{base}, {focus}, {no_text}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan generated card images for OCR text and build a repair manifest.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--min-confidence", type=float, default=0.72)
    parser.add_argument("--min-length", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_metadata_map()
    flagged = scan_for_text(args.min_confidence, args.min_length)

    manifest = []
    seen = set()
    for item in flagged:
        key = (item["subject"], item["step"], item["option_key"])
        meta = metadata.get(key)
        if not meta:
            continue
        seen.add(key)
        manifest.append(
            {
                "subject": meta["subject"],
                "step": meta["step"],
                "option_key": meta["option_key"],
                "title": meta["title"],
                "cue": meta["cue"],
                "prompt": build_notext_prompt(meta),
            }
        )

    for key, meta in metadata.items():
        if meta["subject"] not in FORCE_REPAIR_SUBJECTS:
            continue
        if key in seen:
            continue
        manifest.append(
            {
                "subject": meta["subject"],
                "step": meta["step"],
                "option_key": meta["option_key"],
                "title": meta["title"],
                "cue": meta["cue"],
                "prompt": build_notext_prompt(meta),
            }
        )

    Path(args.output).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.report).write_text(json.dumps(flagged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"flagged={len(flagged)} manifest={len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
