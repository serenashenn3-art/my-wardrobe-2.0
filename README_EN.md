# My Wardrobe 我的衣橱

> Snap a photo · AI de-wrinkles & catalogs · Check to style · One-click outfit cards
>
> A cross-platform agent skill for **Codex / Claude Code / Kimi** and any AI assistant that supports SKILL.md.

[中文 README](README.md)

![demo](docs/demo.gif)

📹 Full demo video: [docs/demo.mp4](docs/demo.mp4)

## What it does

1. **Photo intake** — Send photos of clothes, pants, jewelry, shoes, hats, or bags to your AI; it identifies the category and cuts out the item automatically
2. **AI beautify** — Real-life wrinkles are ironed out by AI image-to-image, producing clean catalog-quality transparent PNGs (prints, collars, and hardware preserved)
3. **Wardrobe management** — Every item is filed into slots (top / bottom / dress / shoes / bag / hat / jewelry…) and tagged with **seasons** (spring / summer / autumn / winter) for seasonal browsing; misclassified items can be moved manually
4. **Check-to-style + drag-to-arrange** — Pick any combination, then **drag items freely** on a 9:16 staging canvas (tap to bring forward, ✕ to remove) until the layout feels right; or ask the AI to style by color, style, or occasion
5. **Outfit cards** — The card is composed from your dragged layout: 9:16 magazine collage (soft shadows, slight rotation, layered composition, Xiaohongshu/RED-ready); a classic 3:4 labeled layout is also included for WeChat/blog use

## Sample output

![sample outfit card](docs/demo-card.png)

## Installation

Clone or download this repo, rename the folder to `my-wardrobe`, and place it in your tool's skills directory:

| Tool | Location |
|------|----------|
| Claude Code | `~/.claude/skills/my-wardrobe/` |
| Codex | `~/.codex/skills/my-wardrobe/` |
| Kimi | Import via skill manager, or place in the skills directory |

Then just say: *"Add this piece to my wardrobe"* or *"Style an outfit from my wardrobe"*.

> Keep the folder name consistent with `name: my-wardrobe` in `SKILL.md`. The Chinese name 「我的衣橱」 is included in the trigger words, so both languages work.

## Repository layout

```
my-wardrobe/
├── SKILL.md                     # Skill entry: workflow & rules (Chinese)
├── scripts/
│   ├── remove_bg.py             # Local background removal (rembg)
│   ├── beautify_item.py         # Local de-wrinkle fallback (OpenCV frequency separation)
│   ├── compose_card.py          # Classic 3:4 labeled outfit card
│   └── compose_card_xhs.py      # 9:16 magazine-collage card (default)
├── references/
│   ├── categories.md            # Item slots, categories & styling rules
│   └── style-guide.md           # Visual specs for both layouts + watermark-removal rules
├── assets/
│   ├── reference-xhs-card.jpg   # 9:16 layout reference
│   └── reference-card.jpeg      # Classic layout reference
└── docs/                        # Demo video, GIF, sample card
```

## Dependencies

- Required: `python3` + `Pillow` (card composition)
- Optional: `rembg` (local background removal), `opencv-python-headless` (local de-wrinkle)
- AI-based cutout/beautify uses each platform's built-in image generation first; local scripts are fallbacks

## Quick start

```bash
# 1. Intake: send photos to your AI, or cut out manually
python3 scripts/remove_bg.py photo.jpg -d items/

# 2. Beautify (local fallback when no AI redraw is available)
python3 scripts/beautify_item.py items/item1.png -o items/item1.png

# 3. Compose a magazine-style outfit card
python3 scripts/compose_card_xhs.py spec.json -o outfit.png
```

`spec.json` example:

```json
{
  "title": "法式复古通勤",
  "items": [
    {"image": "items/item15.png", "id": "item15", "slot": "dress"},
    {"image": "items/item40.png", "id": "item40", "slot": "hat"},
    {"image": "items/item20.png", "id": "item20", "slot": "shoes"},
    {"image": "items/item37.png", "id": "item37", "slot": "bag"}
  ]
}
```

Available slots: `dress / top / outerwear / bottom / shoes / bag / hat / jewelry / scarf / socks / accessory`.

## License

MIT
