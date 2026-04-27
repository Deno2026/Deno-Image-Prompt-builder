# Card Replacement Workflow

## Goal

새 상위 모델이나 더 좋은 ComfyUI 워크플로우를 찾았을 때, 기존 카드 자산을 배치 단위로 다시 생성해서 `assets/cards` 전체를 깔끔하게 교체합니다.

## Source files

- 전체 카드 카탈로그: `scripts/card_replacement_catalog.v1.json`
- 교체 배치 계획: `scripts/card_replacement_plan.v1.json`
- 배치별 manifest: `scripts/replacement_batches/*.json`

## Recommended order

1. `01-home-and-video-entry`
2. `02-video-core`
3. `03-image-human`
4. `04-image-nonhuman-core`
5. `05-image-longtail`

## Build or refresh the replacement plan

```powershell
& "D:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\python_embeded\python.exe" `
  "C:\Users\aions\Documents\Codex\2026-04-17-deno-review\Deno-Image-Prompt-builder\scripts\build_card_replacement_plan.py"
```

## Dry-run a batch

```powershell
& "D:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\python_embeded\python.exe" `
  "C:\Users\aions\Documents\Codex\2026-04-17-deno-review\Deno-Image-Prompt-builder\scripts\generate_card_assets.py" `
  --manifest "C:\Users\aions\Documents\Codex\2026-04-17-deno-review\Deno-Image-Prompt-builder\scripts\replacement_batches\01-home-and-video-entry.json" `
  --dry-run `
  --disable-loras `
  --ratio-preset "Custom" `
  --latent-width 1536 `
  --latent-height 864 `
  --resize-width 1600 `
  --resize-height 800 `
  --webp-quality 72
```

## Run a real replacement batch

```powershell
& "D:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\python_embeded\python.exe" `
  "C:\Users\aions\Documents\Codex\2026-04-17-deno-review\Deno-Image-Prompt-builder\scripts\generate_card_assets.py" `
  --manifest "C:\Users\aions\Documents\Codex\2026-04-17-deno-review\Deno-Image-Prompt-builder\scripts\replacement_batches\02-video-core.json" `
  --overwrite `
  --disable-loras `
  --ratio-preset "Custom" `
  --latent-width 1536 `
  --latent-height 864 `
  --resize-width 1600 `
  --resize-height 800 `
  --webp-quality 72
```

## Notes

- 현재 카드 UI는 `object-fit: cover` 기반이라 `1:1`보다 `16:9` 생성본이 안전합니다.
- `--disable-loras`는 영상 카드처럼 글자/콜라주 artifact가 많이 생기던 경우에 특히 유용합니다.
- 새 워크플로우를 쓰더라도 `CLIPTextEncode`와 `SaveImage` 구조만 비슷하면 기존 스크립트를 유지한 채 재사용하기 쉽습니다.
