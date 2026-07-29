#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_studio_cards.py — 棚拍级单品图生成器 (rembg 精准去背景版)。

对每件单品:
1. 优先使用 AI 生成的平铺图(-flat.jpg / -flatlay.jpg) — 用 rembg 精准去背景
2. 无平铺图时回退到 rembg 透明抠图 + 棚拍增强
3. 统一放置在 1500x1500 奶油米色(#F5F1E8)画布上
4. 底部添加品牌名(有品牌)或样式种类(无品牌)

用法:
    # 基本用法: 读 wardrobe.json, 从 items/ 取抠图, 从 closet-studio/ 取 AI 平铺图, 输出到 closet-studio/
    python3 make_studio_cards.py wardrobe.json

    # 指定输出目录 (AI 平铺图仍从默认 closet-studio/ 读取)
    python3 make_studio_cards.py wardrobe.json -o output/

    # 分别指定 AI 平铺图输入目录和 card 输出目录
    python3 make_studio_cards.py wardrobe.json --flat-dir closet-studio/ --outdir cards/

    # 指定抠图目录和 AI 平铺图输入目录
    python3 make_studio_cards.py wardrobe.json -i items/ --flat-dir closet-studio/

    # 自定义背景色和画布大小
    python3 make_studio_cards.py wardrobe.json --bg 255,255,255 --canvas 1200

依赖: Pillow, numpy, rembg
"""

import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

# 默认参数
DEFAULT_BG = (245, 241, 232)       # 奶油米色 #F5F1E8
DEFAULT_CANVAS = 1500
DEFAULT_MARGIN = 0.08
LABEL_AREA_H = 160
WATERMARK_CROP_RATIO = 0.06       # 裁掉底部 6% 去除 AI 水印

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


def find_flat_image(item, flat_dir):
    """查找 AI 平铺图: -flat.jpg > -flatlay-v2.jpg > -flatlay.jpg

    Args:
        item: 单品字典
        flat_dir: AI 平铺图输入目录 (只读, 不做输出)
    """
    stem = Path(item["file"]).stem
    for name in [f"{stem}-flat.jpg", f"{stem}-flatlay-v2.jpg", f"{stem}-flatlay.jpg"]:
        p = flat_dir / name
        if p.exists():
            return p
    return None


# ═══ rembg 精准去背景 ═══

def remove_background_rembg(im):
    """用 rembg 精准去除背景, 适用于 AI 平铺图(水彩/渐变背景也能处理)。"""
    from rembg import remove
    buf = io.BytesIO()
    im.convert("RGBA").save(buf, format="PNG")
    buf.seek(0)
    result = remove(buf.read())
    out = Image.open(io.BytesIO(result)).convert("RGBA")
    return out


def crop_watermark_area(im, ratio=0.06):
    """裁掉 AI 图底部可能存在的水印/文字区域。"""
    w, h = im.size
    crop_h = int(h * ratio)
    return im.crop((0, 0, w, h - crop_h))


# ═══ 边缘羽化 + 去白边 ═══

def feather_alpha(im, radius=0.8):
    """对 alpha 通道做轻微高斯模糊, 使边缘自然羽化。"""
    arr = np.array(im)
    alpha = Image.fromarray(arr[..., 3], "L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius))
    arr[..., 3] = np.array(alpha)
    return Image.fromarray(arr, "RGBA")


def decontaminate_edges(im, bg_color, threshold=220):
    """去除抠图边缘的白色/浅色光晕(颜色污染)。

    将半透明区域中的白色像素替换为背景色,
    消除 rembg 抠图常见的白边光晕。
    """
    arr = np.array(im).astype(np.uint8)
    alpha = arr[..., 3]
    rgb = arr[..., :3]
    alpha_clean = np.where(alpha < 15, 0, alpha)
    is_light = np.all(rgb > threshold, axis=-1)
    is_semi = (alpha_clean > 0) & (alpha_clean < 250)
    decon_mask = is_semi & is_light
    arr[decon_mask, 0] = bg_color[0]
    arr[decon_mask, 1] = bg_color[1]
    arr[decon_mask, 2] = bg_color[2]
    arr[..., 3] = alpha_clean
    return Image.fromarray(arr, "RGBA")


# ═══ 色彩/光影增强 ═══

def suppress_shadows(im, strength=0.55):
    """压平衣物上的阴影, 使光照更均匀。"""
    arr = np.array(im).astype(np.float32) / 255.0
    alpha = arr[..., 3]
    rgb = arr[..., :3]
    mask = alpha > 0.3
    if not mask.any():
        return im
    luminance = rgb.mean(axis=-1)
    lum_masked = np.where(mask, luminance, -1)
    lum_8bit = (lum_masked.clip(0, 1) * 255).astype(np.uint8)
    lum_img = Image.fromarray(lum_8bit, "L")
    shadow_map = lum_img.filter(ImageFilter.GaussianBlur(50))
    shadow_arr = np.array(shadow_map).astype(np.float32) / 255.0
    valid = mask & (shadow_arr > 0)
    if valid.any():
        mean_lum = luminance[mask].mean()
        compensation = np.zeros_like(luminance)
        compensation[valid] = (mean_lum - shadow_arr[valid]) * strength
        compensation = np.clip(compensation, 0, 0.3)
        for c in range(3):
            rgb[..., c] = np.clip(rgb[..., c] + compensation, 0, 1)
    arr[..., :3] = rgb
    return Image.fromarray((arr * 255).astype(np.uint8), "RGBA")


def auto_levels(im):
    """自动色阶: 拉伸直方图使色彩更饱满。"""
    arr = np.array(im).astype(np.float32)
    alpha = arr[..., 3]
    mask = alpha > 30
    if not mask.any():
        return im
    for c in range(3):
        ch = arr[..., c]
        vals = ch[mask]
        if vals.size == 0:
            continue
        lo = np.percentile(vals, 2)
        hi = np.percentile(vals, 98)
        if hi - lo < 5:
            continue
        stretched = (ch - lo) / (hi - lo) * 245 + 5
        arr[..., c] = np.where(mask, np.clip(stretched, 0, 255), ch)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def enhance_flat(im):
    """AI 平铺图增强: 轻度色彩+锐化(保留 AI 质感)。"""
    im = ImageEnhance.Color(im).enhance(1.05)
    im = ImageEnhance.Brightness(im).enhance(1.03)
    im = ImageEnhance.Contrast(im).enhance(1.04)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=3))
    return im


def enhance_cutout(im, bg_color):
    """rembg 抠图的棚拍增强管线。"""
    im = decontaminate_edges(im, bg_color)
    im = feather_alpha(im, 0.6)
    im = auto_levels(im)
    im = suppress_shadows(im, strength=0.60)
    im = ImageEnhance.Color(im).enhance(1.12)
    im = ImageEnhance.Brightness(im).enhance(1.06)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))
    return im


def enhance_flat_rembg(im, bg_color):
    """AI 平铺图 rembg 去背景后的增强管线。"""
    im = decontaminate_edges(im, bg_color)
    im = feather_alpha(im, 0.8)
    im = suppress_shadows(im, strength=0.45)
    im = enhance_flat(im)
    return im


# ═══ 柔和投影 ═══

def add_soft_shadow(im, offset_y=6, blur=12, opacity=20):
    w, h = im.size
    pad = blur + offset_y + 4
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    alpha = im.split()[-1]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_alpha = Image.new("L", (w, h), 0)
    shadow_alpha.paste(opacity, mask=alpha)
    shadow.putalpha(shadow_alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(shadow, (pad, pad + offset_y), shadow)
    canvas.paste(im, (pad, pad), im)
    return canvas


# ═══ 单品处理 ═══

def process_item(item, items_dir, flat_dir, out_dir, bg_color, canvas_size, margin_pct):
    """处理单件单品, 生成棚拍级 card 图。

    Args:
        item: 单品字典
        items_dir: rembg 抠图目录 (透明底 PNG 输入)
        flat_dir: AI 平铺图输入目录 (只读)
        out_dir: card 图输出目录
        bg_color: 背景色 (R, G, B)
        canvas_size: 画布尺寸
        margin_pct: 内边距比例
    """
    stem = Path(item["file"]).stem

    flat_path = find_flat_image(item, flat_dir)
    photo_path = items_dir / f"{item.get('photo', '')}.png"

    if flat_path:
        # AI 平铺图: 裁水印 -> rembg 去背景 -> 增强
        src = Image.open(flat_path).convert("RGBA")
        src = crop_watermark_area(src, WATERMARK_CROP_RATIO)
        src = remove_background_rembg(src)
        src = enhance_flat_rembg(src, bg_color)
        src_type = "flat"
    elif photo_path.exists():
        # rembg 抠图: 棚拍增强管线
        src = Image.open(photo_path).convert("RGBA")
        src = enhance_cutout(src, bg_color)
        src_type = "cutout"
    else:
        print(f"[skip] 缺图: item{item['id']} {stem}")
        return False

    bbox = src.split()[-1].getbbox()
    if bbox:
        src = src.crop(bbox)
    if src.width < 10 or src.height < 10:
        print(f"[skip] 主体过小: item{item['id']}")
        return False

    canvas = Image.new("RGBA", (canvas_size, canvas_size), bg_color + (255,))

    img_area_h = canvas_size - LABEL_AREA_H
    avail_w = int(canvas_size * (1 - 2 * margin_pct))
    avail_h = int(img_area_h * (1 - 2 * margin_pct))

    scale = min(avail_w / src.width, avail_h / src.height)
    nw = max(1, int(src.width * scale))
    nh = max(1, int(src.height * scale))
    src = src.resize((nw, nh), Image.LANCZOS)

    shadowed = add_soft_shadow(src, offset_y=6, blur=12, opacity=20)
    shadow_pad = 12 + 6 + 4
    actual_w = nw + shadow_pad * 2
    actual_h = nh + shadow_pad * 2
    ox = (canvas_size - actual_w) // 2
    oy = (img_area_h - actual_h) // 2
    canvas.paste(shadowed, (ox, oy), shadowed)

    # 底部标签
    label_text = get_label_text(item)
    draw = ImageDraw.Draw(canvas)
    line_y = canvas_size - LABEL_AREA_H + 20
    draw.line(
        [(int(canvas_size * 0.15), line_y), (int(canvas_size * 0.85), line_y)],
        fill=(200, 192, 175, 180), width=2
    )

    text_len = len(label_text)
    font_size = (
        72 if text_len <= 8 else
        62 if text_len <= 12 else
        54 if text_len <= 16 else
        46 if text_len <= 20 else
        38
    )
    has_brand = bool(item.get("brand", ""))
    font = load_font(font_size, weight="bold" if has_brand else "regular")

    bbox_t = draw.textbbox((0, 0), label_text, font=font)
    tw = bbox_t[2] - bbox_t[0]
    th = bbox_t[3] - bbox_t[1]
    tx = (canvas_size - tw) // 2 - bbox_t[0]
    ty = line_y + 20 + (LABEL_AREA_H - 40 - th) // 2
    color = (55, 48, 38, 255) if has_brand else (110, 100, 85, 255)
    draw.text((tx, ty), label_text, fill=color, font=font)

    out_path = out_dir / f"{stem}-card.png"
    canvas.convert("RGB").save(out_path, quality=95)
    print(f"[ok] item{item['id']} {stem} ({src_type}) -> {label_text}")
    return True


def main():
    ap = argparse.ArgumentParser(
        description="棚拍级单品图生成器 (rembg 精准去背景 + 统一画布 + 底部标签)"
    )
    ap.add_argument("wardrobe", help="wardrobe.json 路径")
    ap.add_argument("-o", "--outdir", default=None,
                    help="card 图输出目录 (默认与 wardrobe.json 同目录下的 closet-studio/)")
    ap.add_argument("-i", "--items-dir", default=None,
                    help="rembg 抠图目录 (默认与 wardrobe.json 同目录下的 items/)")
    ap.add_argument("--flat-dir", default=None,
                    help="AI 平铺图输入目录 (默认与 wardrobe.json 同目录下的 closet-studio/; 只读不写入)")
    ap.add_argument("-s", "--studio-dir", default=None,
                    help="[已废弃] 旧参数, 同时作为 AI 平铺图输入和 card 输出目录。"
                         "新代码请用 --flat-dir 和 --outdir 分别指定。"
                         "若仍传入, 则 flat-dir 和 outdir 都设为此值")
    ap.add_argument("--bg", default="245,241,232",
                    help="背景色 R,G,B (默认 245,241,232 = #F5F1E8)")
    ap.add_argument("--canvas", type=int, default=DEFAULT_CANVAS,
                    help=f"画布尺寸 (默认 {DEFAULT_CANVAS})")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN,
                    help=f"内边距比例 (默认 {DEFAULT_MARGIN})")
    args = ap.parse_args()

    wardrobe_path = Path(args.wardrobe).resolve()
    root = wardrobe_path.parent
    items_dir = Path(args.items_dir).resolve() if args.items_dir else root / "items"

    # 拆分输入/输出目录:
    #   flat_dir  = AI 平铺图输入目录 (只读)
    #   out_dir   = card 图输出目录 (只写)
    # 兼容旧 -s/--studio-dir 参数: 同时作为输入和输出
    if args.studio_dir:
        flat_dir = Path(args.studio_dir).resolve()
        out_dir = Path(args.studio_dir).resolve()
    else:
        flat_dir = Path(args.flat_dir).resolve() if args.flat_dir else root / "closet-studio"
        out_dir = Path(args.outdir).resolve() if args.outdir else root / "closet-studio"

    out_dir.mkdir(parents=True, exist_ok=True)

    bg_color = tuple(int(x) for x in args.bg.split(","))

    wardrobe = json.loads(wardrobe_path.read_text(encoding="utf-8"))
    items = wardrobe["items"]

    print(f"衣橱: {wardrobe_path.name}  共 {len(items)} 件")
    print(f"抠图目录(输入): {items_dir}")
    print(f"AI平铺图目录(输入): {flat_dir}")
    print(f"输出目录: {out_dir}")
    print(f"背景色: {bg_color}  画布: {args.canvas}px\n")

    n_ok = sum(
        1 for item in items
        if process_item(item, items_dir, flat_dir, out_dir, bg_color, args.canvas, args.margin)
    )
    print(f"\n完成: {n_ok}/{len(items)} 件")


if __name__ == "__main__":
    main()
