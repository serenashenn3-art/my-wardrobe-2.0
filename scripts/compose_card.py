#!/usr/bin/env python3
"""compose_card.py — 杂志拼贴风「搭配样式卡」合成器.

输入一份 JSON 搭配清单(白底/透明底单品抠图 + 标签 + 槽位),输出一张
白底杂志拼贴风搭配卡 PNG。排版规则见 references/style-guide.md。

用法:
    python3 compose_card.py spec.json -o card.png

spec.json 结构:
{
  "canvas": {"width": 1200, "height": 1600},          // 可选,默认 3:4
  "title": "周一通勤",                                  // 可选,左上角小标题
  "items": [
    {
      "image": "items/white-tee.png",                  // 必填,透明底 PNG 最佳
      "label": "COS",                                  // 可选,品牌/单品名
      "slot": "top"                                    // 必填,见 SLOTS
    }
  ]
}

slot 取值: top / bottom / dress / shoes / bag / hat / jewelry / scarf /
socks / outerwear / accessory
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- fonts
FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Times.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    # Windows
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/times.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/arial.ttf",
]


CJK_FONTS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]


def has_cjk(text):
    return any("一" <= ch <= "鿿" for ch in text)


def load_font(size, text=""):
    candidates = list(FONT_CANDIDATES)
    if has_cjk(text):
        candidates = CJK_FONTS + candidates
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ------------------------------------------------------- layout zones
# 每个槽位一个相对布局区: (cx, cy) 为中心, (zw, zh) 为最大占用,均为画幅比例。
# 规则来源: references/style-guide.md
ZONES = {
    "top":       {"center": (0.27, 0.20), "span": (0.44, 0.34), "label": "above"},
    "outerwear": {"center": (0.27, 0.22), "span": (0.46, 0.38), "label": "above"},
    "dress":     {"center": (0.42, 0.52), "span": (0.56, 0.70), "label": "above"},
    "bottom":    {"center": (0.55, 0.60), "span": (0.40, 0.66), "label": "below"},
    "bag":       {"center": (0.18, 0.68), "span": (0.28, 0.26), "label": "below"},
    "shoes":     {"center": (0.83, 0.80), "span": (0.28, 0.30), "label": "below"},
    "hat":       {"center": (0.76, 0.14), "span": (0.24, 0.18), "label": "above"},
    "scarf":     {"center": (0.76, 0.16), "span": (0.30, 0.20), "label": "above"},
    "jewelry":   {"center": (0.80, 0.40), "span": (0.20, 0.14), "label": "below"},
    "socks":     {"center": (0.66, 0.86), "span": (0.14, 0.12), "label": "below"},
    "accessory": {"center": (0.80, 0.40), "span": (0.22, 0.16), "label": "below"},
}

# 同槽位多件时的水平错开步长(画幅比例)
MULTI_OFFSET = 0.13

BG = (255, 255, 255, 255)
LABEL_COLOR = (26, 26, 26)
TITLE_COLOR = (120, 120, 120)


def trim_alpha(img, threshold=8):
    """裁掉透明边缘,返回裁剪后的图。"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a > threshold else 0).getbbox()
    return img.crop(bbox) if bbox else img


def flatten_white(img):
    """非透明图贴到白底上(避免黑边)。"""
    if img.mode == "RGBA":
        base = Image.new("RGBA", img.size, BG)
        base.alpha_composite(img)
        return base
    return img.convert("RGBA")


def fit_into(img, max_w, max_h):
    """等比缩放到 (max_w, max_h) 以内。"""
    w, h = img.size
    if w == 0 or h == 0:
        return img
    scale = min(max_w / w, max_h / h)
    if scale >= 1:
        return img
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                      Image.LANCZOS)


def draw_label(draw, text, cx, y, font, align="center"):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text((cx - w / 2, y + i * font.size * 1.25), line,
                  font=font, fill=LABEL_COLOR)


def compose(spec, out_path):
    cw = spec.get("canvas", {}).get("width", 1200)
    ch = spec.get("canvas", {}).get("height", 1600)
    canvas = Image.new("RGBA", (cw, ch), BG)
    draw = ImageDraw.Draw(canvas)

    label_size = max(18, ch // 55)
    all_text = spec.get("title", "") + "".join(
        i.get("label", "") for i in spec["items"])
    font = load_font(label_size, all_text)
    title_font = load_font(max(14, ch // 70), spec.get("title", ""))

    if spec.get("title"):
        draw.text((cw * 0.04, ch * 0.015), spec["title"],
                  font=title_font, fill=TITLE_COLOR)

    # 按槽位分组,保序
    groups = {}
    for item in spec["items"]:
        slot = item.get("slot", "accessory")
        if slot not in ZONES:
            print(f"[warn] 未知 slot '{slot}',按 accessory 处理", file=sys.stderr)
            slot = "accessory"
        groups.setdefault(slot, []).append(item)

    # 绘制顺序:大件先画,小件后画(小件可在上层轻微叠压)
    order = ["dress", "bottom", "top", "outerwear", "bag",
             "shoes", "socks", "scarf", "hat", "jewelry", "accessory"]

    for slot in order:
        items = groups.get(slot)
        if not items:
            continue
        zone = ZONES[slot]
        cx0, cy0 = zone["center"]
        zw, zh = zone["span"]
        max_w, max_h = int(cw * zw), int(ch * zh)

        for idx, item in enumerate(items):
            path = item["image"]
            if not os.path.exists(path):
                print(f"[warn] 找不到图片 {path},跳过", file=sys.stderr)
                continue
            img = Image.open(path)
            img = trim_alpha(img)
            img = flatten_white(img) if img.mode != "RGBA" else img
            # 多件时逐件缩小一点
            shrink = 1.0 if len(items) == 1 else 1.0 / math.sqrt(len(items))
            img = fit_into(img, int(max_w * shrink), int(max_h * shrink))

            # 多件水平错开
            off = (idx - (len(items) - 1) / 2) * MULTI_OFFSET * cw
            cx = int(cx0 * cw + off)
            cy = int(cy0 * ch)
            x, y = cx - img.width // 2, cy - img.height // 2
            canvas.alpha_composite(img, (x, y))

            label = item.get("label", "").strip()
            if label:
                if zone["label"] == "above":
                    draw_label(draw, label, cx, y - label_size * 1.6, font)
                else:
                    draw_label(draw, label, cx, y + img.height + label_size * 0.4,
                               font)

    canvas.convert("RGB").save(out_path, "PNG")
    print(f"已生成: {out_path} ({cw}x{ch}, {len(spec['items'])} 件单品)")


def main():
    ap = argparse.ArgumentParser(description="合成杂志拼贴风搭配样式卡")
    ap.add_argument("spec", help="搭配清单 JSON 文件")
    ap.add_argument("-o", "--output", default="outfit-card.png", help="输出 PNG 路径")
    args = ap.parse_args()

    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)
    if not spec.get("items"):
        sys.exit("spec 中缺少 items")
    compose(spec, args.output)


if __name__ == "__main__":
    main()
