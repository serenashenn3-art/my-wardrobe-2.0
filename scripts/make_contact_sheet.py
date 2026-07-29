#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_contact_sheet.py — 衣橱预览墙生成器。

读取 wardrobe.json, 从 card 目录取出每件单品的棚拍级 card 图,
排列成 N 列网格预览墙, 每张图下方附带品牌/样式标签。

用法:
    python3 make_contact_sheet.py wardrobe.json
    python3 make_contact_sheet.py wardrobe.json -s closet-studio/ -o closet-overview.png
    python3 make_contact_sheet.py wardrobe.json --cols 5 --cell 400

依赖: Pillow
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_BG = (245, 241, 232)   # 奶油米色 #F5F1E8
DEFAULT_COLS = 4
DEFAULT_CELL = 480
DEFAULT_LABEL_H = 50
DEFAULT_GAP = 16
DEFAULT_MARGIN = 50

SLOT_CN = {
    "dress": "连衣裙", "top": "上装", "bottom": "下装",
    "shoes": "鞋", "bag": "包", "hat": "帽子",
    "jewelry": "首饰", "socks": "袜子", "outerwear": "外套",
    "accessory": "配饰", "scarf": "丝巾",
}


def load_font(size, weight="regular"):
    """加载系统 CJK 字体, 支持 macOS / Linux / Windows。"""
    cands = {
        "regular": [
            "/System/Library/Fonts/PingFang.ttc:0",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ],
        "bold": [
            "/System/Library/Fonts/PingFang.ttc:1",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
        ],
    }[weight]
    for cand in cands:
        if ":" in cand:
            p, idx = cand.rsplit(":", 1)
            if Path(p).exists():
                try:
                    return ImageFont.truetype(p, size, index=int(idx))
                except (OSError, IOError, ValueError):
                    continue
        elif Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def get_label_text(item):
    """有品牌写品牌, 无品牌写品类·样式。"""
    brand = item.get("brand", "")
    if brand:
        return brand
    slot = item.get("slot", "")
    slot_cn = SLOT_CN.get(slot, slot)
    style = item.get("style", "")
    if style:
        return f"{slot_cn} · {style}"
    return slot_cn


def find_card(item, studio_dir):
    """查找单品 card 图: {stem}-card.png"""
    stem = Path(item["file"]).stem
    p = studio_dir / f"{stem}-card.png"
    return p if p.exists() else None


def main():
    ap = argparse.ArgumentParser(description="衣橱预览墙生成器")
    ap.add_argument("wardrobe", help="wardrobe.json 路径")
    ap.add_argument("-s", "--studio-dir", default=None,
                    help="card 图目录 (默认与 wardrobe.json 同目录下的 closet-studio/)")
    ap.add_argument("-o", "--output", default=None,
                    help="输出文件路径 (默认与 wardrobe.json 同目录下的 closet-overview.png)")
    ap.add_argument("--cols", type=int, default=DEFAULT_COLS,
                    help=f"列数 (默认 {DEFAULT_COLS})")
    ap.add_argument("--cell", type=int, default=DEFAULT_CELL,
                    help=f"单品图尺寸 px (默认 {DEFAULT_CELL})")
    ap.add_argument("--bg", default="245,241,232",
                    help="背景色 R,G,B (默认 245,241,232 = #F5F1E8)")
    args = ap.parse_args()

    wardrobe_path = Path(args.wardrobe).resolve()
    root = wardrobe_path.parent
    studio_dir = Path(args.studio_dir).resolve() if args.studio_dir else root / "closet-studio"
    out_path = Path(args.output).resolve() if args.output else root / "closet-overview.png"

    bg = tuple(int(x) for x in args.bg.split(","))
    cols = args.cols
    cell = args.cell
    label_h = DEFAULT_LABEL_H
    gap = DEFAULT_GAP
    margin = DEFAULT_MARGIN

    wardrobe = json.loads(wardrobe_path.read_text(encoding="utf-8"))
    items = wardrobe["items"]

    n = len(items)
    rows = (n + cols - 1) // cols
    cell_total = cell + label_h
    W = cols * cell + (cols - 1) * gap + 2 * margin
    H = rows * cell_total + (rows - 1) * gap + 2 * margin
    sheet = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(sheet)

    font_brand = load_font(28, weight="bold")
    font_style = load_font(24, weight="regular")
    color_brand = (55, 48, 38)
    color_style = (110, 100, 85)

    n_ok = 0
    for i, it in enumerate(items):
        r, c = divmod(i, cols)
        x = margin + c * (cell + gap)
        y = margin + r * (cell_total + gap)

        path = find_card(it, studio_dir)
        if not path:
            print(f"[warn] 缺图: item{it['id']} {it.get('file', '')}")
            continue

        im = Image.open(path).convert("RGB")
        im = im.resize((cell, cell), Image.LANCZOS)
        sheet.paste(im, (x, y))

        label = get_label_text(it)
        has_brand = bool(it.get("brand", ""))
        font = font_brand if has_brand else font_style
        color = color_brand if has_brand else color_style

        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        tx = x + (cell - tw) // 2 - bbox[0]
        ty = y + cell + 8
        draw.text((tx, ty), label, fill=color, font=font)

        n_ok += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=95)
    print(f"已生成: {out_path}  尺寸 {sheet.size[0]}x{sheet.size[1]}  共 {n_ok} 件")


if __name__ == "__main__":
    main()
