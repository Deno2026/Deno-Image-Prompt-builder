from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_missing_card_manifest import REPO_ROOT, build_image_manifest
ASSET_DIR = REPO_ROOT / "assets" / "cards"
HOME_MANIFEST = SCRIPTS_DIR / "comfy_card_manifest.home.v1.json"
VIDEO_MANIFEST = SCRIPTS_DIR / "comfy_video_card_manifest.v1.json"
DEFAULT_CATALOG = SCRIPTS_DIR / "card_replacement_catalog.v1.json"
DEFAULT_PLAN = SCRIPTS_DIR / "card_replacement_plan.v1.json"
DEFAULT_BATCH_DIR = SCRIPTS_DIR / "replacement_batches"

HUMAN_SUBJECTS = {
    "thumbnail-person",
    "portrait",
    "selfie-sns",
    "group-family",
    "fashion-beauty",
    "profile-id",
}

PRIMARY_NONHUMAN_SUBJECTS = {
    "product",
    "food-drink",
    "landscape",
    "travel",
    "service",
    "space",
    "architecture",
    "vehicle",
    "animal",
    "workspace",
}

LONGTAIL_NONHUMAN_SUBJECTS = {
    "poster",
    "fantasy",
    "illustration",
    "event",
    "broll",
    "subjects",
}

BATCH_DEFS = [
    {
        "name": "01-home-and-video-entry",
        "description": "메인 첫인상과 영상 첫 선택 화면부터 교체하는 배치",
        "criteria": lambda item: item["page"] == "home"
        or (item["page"] == "video" and item["step"] == "start"),
        "recommended_ratio": "16:9",
    },
    {
        "name": "02-video-core",
        "description": "동영상 생성기 T2V 전 단계 카드 교체 배치",
        "criteria": lambda item: item["page"] == "video" and item["step"] != "start",
        "recommended_ratio": "16:9",
    },
    {
        "name": "03-image-human",
        "description": "사람 관련 이미지 카드 교체 배치",
        "criteria": lambda item: item["page"] == "image" and item["subject"] in HUMAN_SUBJECTS,
        "recommended_ratio": "16:9",
    },
    {
        "name": "04-image-nonhuman-core",
        "description": "제품/풍경/공간 등 주요 비인물 카드 교체 배치",
        "criteria": lambda item: item["page"] == "image" and item["subject"] in PRIMARY_NONHUMAN_SUBJECTS,
        "recommended_ratio": "16:9",
    },
    {
        "name": "05-image-longtail",
        "description": "포스터/판타지/B-roll 등 롱테일 카드 교체 배치",
        "criteria": lambda item: item["page"] == "image" and item["subject"] in LONGTAIL_NONHUMAN_SUBJECTS,
        "recommended_ratio": "16:9",
    },
]


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_item(
    page: str,
    subject: str,
    step: str,
    option_key: str,
    title: str,
    cue: str = "",
    prompt: str = "",
) -> dict:
    asset_path = ASSET_DIR / subject / step / f"{option_key}.webp"
    return {
        "page": page,
        "subject": subject,
        "step": step,
        "option_key": option_key,
        "title": title,
        "cue": cue,
        "prompt": prompt,
        "asset_path": str(asset_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "asset_exists": asset_path.exists(),
        "recommended_ratio": "16:9",
    }


def load_home_items() -> list[dict]:
    items = []
    for raw in load_json(HOME_MANIFEST):
        items.append(
            normalize_item(
                page="home",
                subject=raw["subject"],
                step=raw["step"],
                option_key=raw["option_key"],
                title=raw.get("title", raw["option_key"]),
                cue=raw.get("cue", ""),
                prompt=raw.get("prompt", ""),
            )
        )
    return items


def load_video_items() -> list[dict]:
    items = []
    for raw in load_json(VIDEO_MANIFEST):
        items.append(
            normalize_item(
                page="video",
                subject=raw["subject"],
                step=raw["step"],
                option_key=raw["option_key"],
                title=raw.get("title", raw["option_key"]),
                cue=raw.get("cue", ""),
                prompt=raw.get("prompt", ""),
            )
        )
    return items


def load_image_items() -> list[dict]:
    items = []
    for raw in build_image_manifest(include_existing=True):
        items.append(
            normalize_item(
                page="image",
                subject=raw["subject"],
                step=raw["step"],
                option_key=raw["option_key"],
                title=raw.get("title", raw["option_key"]),
                cue=raw.get("cue", ""),
            )
        )
    return items


def build_catalog() -> list[dict]:
    catalog = load_home_items() + load_video_items() + load_image_items()
    seen = set()
    unique = []
    for item in catalog:
        key = (item["page"], item["subject"], item["step"], item["option_key"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_batches(catalog: list[dict], batch_dir: Path) -> dict:
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_entries = []

    for batch in BATCH_DEFS:
        items = [item for item in catalog if batch["criteria"](item)]
        manifest_path = batch_dir / f"{batch['name']}.json"
        write_json(
            manifest_path,
            [
                {
                    "subject": item["subject"],
                    "step": item["step"],
                    "option_key": item["option_key"],
                    "title": item["title"],
                    "cue": item["cue"],
                    **({"prompt": item["prompt"]} if item["prompt"] else {}),
                }
                for item in items
            ],
        )
        batch_entries.append(
            {
                "name": batch["name"],
                "description": batch["description"],
                "recommended_ratio": batch["recommended_ratio"],
                "count": len(items),
                "manifest": str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "pages": sorted({item["page"] for item in items}),
                "subjects": sorted({item["subject"] for item in items}),
            }
        )

    return {
        "total_items": len(catalog),
        "batches": batch_entries,
    }


def build_plan(catalog: list[dict], batch_dir: Path) -> dict:
    batch_info = build_batches(catalog, batch_dir)
    expected = {item["asset_path"] for item in catalog}
    actual = {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for path in ASSET_DIR.rglob("*.webp")
    }
    orphan_assets = sorted(actual - expected)
    return {
        "summary": {
            "total_cards": len(catalog),
            "home_cards": sum(1 for item in catalog if item["page"] == "home"),
            "video_cards": sum(1 for item in catalog if item["page"] == "video"),
            "image_cards": sum(1 for item in catalog if item["page"] == "image"),
            "existing_assets": sum(1 for item in catalog if item["asset_exists"]),
            "orphan_assets": len(orphan_assets),
            "orphan_asset_paths": orphan_assets,
            "recommended_default_ratio": "16:9",
            "notes": [
                "현재 카드 썸네일은 object-fit: cover 기반이라 1:1보다 16:9 생성본이 안전합니다.",
                "교체는 첫인상 배치 -> 영상 배치 -> 사람 카드 -> 비인물 카드 순서가 효율적입니다.",
                "새 상위 모델을 찾으면 이 배치 manifest를 그대로 generate_card_assets.py에 넣어 재생성하면 됩니다.",
            ],
        },
        "batch_plan": batch_info["batches"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a full card-replacement catalog and batch manifests.")
    parser.add_argument("--catalog-output", default=str(DEFAULT_CATALOG))
    parser.add_argument("--plan-output", default=str(DEFAULT_PLAN))
    parser.add_argument("--batch-dir", default=str(DEFAULT_BATCH_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = build_catalog()
    catalog_path = Path(args.catalog_output)
    plan_path = Path(args.plan_output)
    batch_dir = Path(args.batch_dir)

    write_json(catalog_path, catalog)
    plan = build_plan(catalog, batch_dir)
    write_json(plan_path, plan)

    print(f"Wrote catalog with {len(catalog)} items to {catalog_path}")
    for batch in plan["batch_plan"]:
        print(f"- {batch['name']}: {batch['count']} cards")
    print(f"Wrote replacement plan to {plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
