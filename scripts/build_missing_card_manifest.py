from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_HTML = REPO_ROOT / "image.html"
ASSET_DIR = REPO_ROOT / "assets" / "cards"
DEFAULT_OUTPUT = Path(__file__).with_name("comfy_card_manifest.remaining.auto.json")


# image.html 런타임에서 step.options 대신 다른 옵션 세트를 반환하는 브랜치들.
# 누락 검사는 화면 기준으로 해야 하므로, 정적 FLOW_PROFILES만 보면 빠지는 카드들이 생긴다.
DYNAMIC_OPTION_SETS: dict[str, dict[str, list[str]]] = {
    "thumbnail-person": {
        "people": ["THUMBNAIL_PEOPLE_OPTIONS"],
        "pose": ["THUMBNAIL_POSE_OPTIONS"],
        "text": ["THUMBNAIL_TEXT_OPTIONS"],
        "composition": [
            "THUMBNAIL_COMPOSITION_LEFT_OPTIONS",
            "THUMBNAIL_COMPOSITION_RIGHT_OPTIONS",
            "THUMBNAIL_COMPOSITION_CENTER_OPTIONS",
        ],
    },
    "portrait": {
        "people": ["PORTRAIT_PEOPLE_OPTIONS"],
        "pose": ["PORTRAIT_POSE_OPTIONS"],
        "composition": [
            "PORTRAIT_COMPOSITION_PROFILE_OPTIONS",
            "PORTRAIT_COMPOSITION_EDITORIAL_OPTIONS",
            "PORTRAIT_COMPOSITION_NATURAL_OPTIONS",
        ],
    },
    "selfie-sns": {
        "pose": ["SELFIE_POSE_OPTIONS"],
        "composition": [
            "SELFIE_COMPOSITION_MIRROR_OPTIONS",
            "SELFIE_COMPOSITION_FACE_OPTIONS",
            "SELFIE_COMPOSITION_HALF_OPTIONS",
            "SELFIE_COMPOSITION_WALK_OPTIONS",
        ],
    },
    "group-family": {
        "relation": ["GROUP_RELATION_OPTIONS"],
        "pose": ["GROUP_POSE_OPTIONS"],
        "composition": [
            "GROUP_COMPOSITION_COUPLE_OPTIONS",
            "GROUP_COMPOSITION_FORMAL_OPTIONS",
            "GROUP_COMPOSITION_CASUAL_OPTIONS",
        ],
    },
    "fashion-beauty": {
        "focus": ["FASHION_FOCUS_OPTIONS"],
        "pose": ["FASHION_POSE_OPTIONS"],
        "composition": [
            "FASHION_COMPOSITION_BEAUTY_OPTIONS",
            "FASHION_COMPOSITION_FULL_OPTIONS",
            "FASHION_COMPOSITION_UPPER_OPTIONS",
        ],
    },
    "profile-id": {
        "impression": ["PROFILE_IMPRESSION_OPTIONS"],
        "background": ["PROFILE_BG_OPTIONS"],
        "pose": ["PROFILE_POSE_OPTIONS"],
        "composition": [
            "PROFILE_COMPOSITION_SOCIAL_OPTIONS",
            "PROFILE_COMPOSITION_FORMAL_OPTIONS",
        ],
    },
    "vehicle": {
        "environment": [
            "VEHICLE_ENV_EXTERIOR_OPTIONS",
            "VEHICLE_ENV_INTERIOR_OPTIONS",
        ],
    },
    "space": {
        "composition": [
            "SPACE_COMPOSITION_LIVING_OPTIONS",
            "SPACE_COMPOSITION_BED_OPTIONS",
            "SPACE_COMPOSITION_COMMERCIAL_OPTIONS",
        ],
    },
    "architecture": {
        "composition": [
            "ARCH_COMPOSITION_DETAIL_OPTIONS",
            "ARCH_COMPOSITION_LANDMARK_OPTIONS",
            "ARCH_COMPOSITION_FACADE_OPTIONS",
        ],
    },
    "animal": {
        "composition": [
            "ANIMAL_COMPOSITION_COMPANION_OPTIONS",
            "ANIMAL_COMPOSITION_ACTION_OPTIONS",
            "ANIMAL_COMPOSITION_PORTRAIT_OPTIONS",
        ],
    },
    "workspace": {
        "layout": [
            "WORK_LAYOUT_TALK_OPTIONS",
            "WORK_LAYOUT_DOC_OPTIONS",
        ],
        "composition": [
            "WORK_COMPOSITION_DOC_OPTIONS",
            "WORK_COMPOSITION_DEVICE_OPTIONS",
            "WORK_COMPOSITION_PEOPLE_OPTIONS",
        ],
    },
    "service": {
        "composition": [
            "SERVICE_COMPOSITION_TEAM_OPTIONS",
            "SERVICE_COMPOSITION_UI_OPTIONS",
        ],
    },
    "poster": {
        "composition": [
            "POSTER_COMPOSITION_VISUAL_OPTIONS",
            "POSTER_COMPOSITION_TITLE_OPTIONS",
        ],
    },
    "fantasy": {
        "stage": ["FANTASY_STAGE_OPTIONS"],
        "composition": [
            "FANTASY_COMPOSITION_BATTLE_OPTIONS",
            "FANTASY_COMPOSITION_WORLD_OPTIONS",
            "FANTASY_COMPOSITION_SYMBOLIC_OPTIONS",
            "FANTASY_COMPOSITION_CHARACTER_OPTIONS",
        ],
    },
    "illustration": {
        "usage": ["ILLU_USAGE_OPTIONS"],
        "composition": [
            "ILLU_COMPOSITION_SHEET_OPTIONS",
            "ILLU_COMPOSITION_FULL_OPTIONS",
            "ILLU_COMPOSITION_SCENE_OPTIONS",
            "ILLU_COMPOSITION_FACE_OPTIONS",
        ],
    },
    "event": {
        "moment": ["EVENT_MOMENT_OPTIONS"],
        "composition": [
            "EVENT_COMPOSITION_BACKSTAGE_OPTIONS",
            "EVENT_COMPOSITION_BOOTH_OPTIONS",
            "EVENT_COMPOSITION_AUDIENCE_OPTIONS",
            "EVENT_COMPOSITION_SPEAKER_OPTIONS",
            "EVENT_COMPOSITION_STAGE_OPTIONS",
        ],
    },
    "broll": {
        "detail": ["BROLL_DETAIL_OPTIONS"],
        "usage": ["BROLL_USAGE_OPTIONS"],
        "composition": [
            "BROLL_COMPOSITION_ABSTRACT_OPTIONS",
            "BROLL_COMPOSITION_HAND_OPTIONS",
            "BROLL_COMPOSITION_OBJECT_OPTIONS",
            "BROLL_COMPOSITION_EMPTY_OPTIONS",
            "BROLL_COMPOSITION_SCENIC_OPTIONS",
        ],
    },
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
        r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]'
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
    subject_pattern = re.compile(
        r'(?:\"([^\"]+)\"|(\w+))\s*:\s*\[(.*?)\]\s*(?=,\s*(?:\"|\w)|\s*$)',
        re.S,
    )
    step_pattern = re.compile(r'makeStep\(\s*"([^"]+)".*?,\s*(\w+)\s*\)', re.S)

    subjects: dict[str, list[tuple[str, str]]] = {}
    for subject_match in subject_pattern.finditer(flow_body):
        subject = subject_match.group(1) or subject_match.group(2)
        body = subject_match.group(3)
        subjects[subject] = step_pattern.findall(body)
    return subjects


def derive_asset_path(subject: str, step: str, option_key: str) -> Path:
    return ASSET_DIR / subject / step / f"{option_key}.webp"


def build_image_manifest(
    include_existing: bool = False,
    limit: int = 0,
    subjects_filter: set[str] | None = None,
) -> list[dict]:
    text = load_text(IMAGE_HTML)
    option_sets = parse_option_sets(text)
    flow_profiles = parse_flow_profiles(text)
    subject_options = parse_subject_options(text)

    items: list[dict] = []

    for option_key, title, description in subject_options:
        if subjects_filter and "subjects" not in subjects_filter:
            pass
        else:
            asset_path = derive_asset_path("subjects", "subject", option_key)
            if include_existing or not asset_path.exists():
                items.append(
                    {
                        "subject": "subjects",
                        "step": "subject",
                        "option_key": option_key,
                        "title": title,
                        "cue": description,
                        "asset_path": str(asset_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    }
                )

    for subject, steps in flow_profiles.items():
        if subject == "manual":
            continue
        if subjects_filter and subject not in subjects_filter:
            continue

        for step, option_set in steps:
            option_set_names = [option_set]
            option_set_names.extend(DYNAMIC_OPTION_SETS.get(subject, {}).get(step, []))

            seen_keys: set[str] = set()
            for option_set_name in option_set_names:
                for option_key, title, description in option_sets.get(option_set_name, []):
                    if option_key in seen_keys:
                        continue
                    seen_keys.add(option_key)
                    asset_path = derive_asset_path(subject, step, option_key)
                    if asset_path.exists() and not include_existing:
                        continue
                    items.append(
                        {
                            "subject": subject,
                            "step": step,
                            "option_key": option_key,
                            "title": title,
                            "cue": description,
                            "asset_path": str(asset_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        }
                    )

    if limit:
        items = items[:limit]
    return items


def build_missing_manifest(limit: int = 0, subjects_filter: set[str] | None = None) -> list[dict]:
    return build_image_manifest(
        include_existing=False,
        limit=limit,
        subjects_filter=subjects_filter,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manifest for card options that do not have generated images yet.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument(
        "--mode",
        choices=["missing", "all"],
        default="missing",
        help="Write only missing image cards or the full image-card catalog.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    subjects_filter = set(args.subjects) if args.subjects else None
    manifest = build_image_manifest(
        include_existing=args.mode == "all",
        limit=args.limit,
        subjects_filter=subjects_filter,
    )
    output_path = Path(args.output)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} items to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
