#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「我的衣橱」展示视频的 6 帧场景图 (1080x1080)。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = H = 1080
BG = (250, 248, 245)
INK = (38, 34, 30)
SUB = (150, 142, 128)
ACCENT = (176, 124, 86)
ROOT = Path("/Users/mac/Documents/Kimi/Workspaces/UI设计/outfit-demo")
OUT = Path("/Users/mac/Documents/Kimi/Workspaces/UI设计/my-wardrobe/docs/frames")
OUT.mkdir(parents=True, exist_ok=True)

FONTS = ["/System/Library/Fonts/PingFang.ttc",
         "/System/Library/Fonts/Hiragino Sans GB.ttc",
         "/System/Library/Fonts/STHeiti Medium.ttc"]
SERIF = "/System/Library/Fonts/Supplemental/Songti.ttc"

def font(size, idx=0):
    for p in FONTS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()

def serif(size):
    try:
        return ImageFont.truetype(SERIF, size, index=0)
    except Exception:
        return font(size)

def rounded(im, rad=28):
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], rad, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out

def shadow_paste(canvas, im, x, y, blur=14, dy=10, opacity=70):
    pad = blur * 3
    layer = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    alpha = im.split()[-1].point(lambda a: a * opacity // 255)
    sh = Image.new("RGBA", im.size, (40, 34, 28, 255))
    sh.putalpha(alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    layer.paste(sh, (pad, pad + dy), sh)
    layer.paste(im, (pad, pad), im)
    canvas.paste(layer, (x - pad, y - pad), layer)

def cover(im, w, h):
    """裁剪填充目标尺寸"""
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s + .5), int(im.height * s + .5)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def contain(im, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((int(im.width * s + .5), int(im.height * s + .5)), Image.LANCZOS)

def center_text(d, y, text, f, fill=INK):
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=f, fill=fill)

def base():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)

def step_badge(d, text):
    f = font(30, 0)
    bb = d.textbbox((0, 0), text, font=f)
    tw = bb[2] - bb[0]
    x0 = (W - tw) / 2 - 26
    d.rounded_rectangle([x0, 920, x0 + tw + 52, 976], 28, fill=INK)
    d.text(((W - tw) / 2, 930), text, font=f, fill=(250, 248, 245))

# ---------- 帧 1: 标题 ----------
im, d = base()
# 顶部小字
center_text(d, 200, "MY WARDROBE SKILL", font(30, 0), SUB)
# 主标题
center_text(d, 330, "我的衣橱", serif(120))
d.line([(W/2 - 120, 500), (W/2 + 120, 500)], fill=ACCENT, width=4)
center_text(d, 560, "拍照建档 · AI 美化 · 一键搭配卡", font(44), INK)
center_text(d, 680, "把衣柜里的每一件单品  变成可搭配的杂志卡片", font(32), SUB)
# 底部适配标识
center_text(d, 880, "适配  Codex / Claude Code / Kimi", font(30, 0), SUB)
im.save(OUT / "f1.png")

# ---------- 帧 2: 拍照 ----------
im, d = base()
center_text(d, 80, "随手拍下你的单品", font(52, 0))
center_text(d, 160, "衣服 · 裤子 · 首饰 · 鞋 · 帽 · 包", font(30), SUB)
photos = ["item15.jpg", "item37.jpg", "item20.jpg", "item40.jpg"]
cw, ch, gap = 400, 400, 40
x0 = (W - (cw * 2 + gap)) / 2
y0 = 260
for i, name in enumerate(photos):
    p = Image.open(ROOT / "photos" / name).convert("RGB")
    t = rounded(cover(p, cw, ch))
    x = x0 + (i % 2) * (cw + gap)
    y = y0 + (i // 2) * (ch + gap)
    shadow_paste(im, t, int(x), int(y))
step_badge(d, "① 拍照录入")
im.save(OUT / "f2.png")

# ---------- 帧 3: AI 美化 before/after ----------
im, d = base()
center_text(d, 80, "AI 自动美化", font(52, 0))
center_text(d, 160, "去皱板正 · 透明底 · 电商级单品图", font(30), SUB)
before = Image.open(ROOT / "photos" / "item15.jpg").convert("RGB")
after = Image.open(ROOT / "items-beauty" / "item15.png").convert("RGBA")
bw = 380
b = rounded(cover(before, bw, 500))
# after 贴到白卡上
card = Image.new("RGBA", (bw, 500), (255, 255, 255, 255))
a = contain(after, bw - 30, 470)
card.paste(a, ((bw - a.width) // 2, (500 - a.height) // 2), a)
card = rounded(card)
shadow_paste(im, b, 90, 280)
shadow_paste(im, card, W - 90 - bw, 280)
# 箭头
d.text((W/2 - 30, 480), "→", font=font(60, 0), fill=ACCENT)
d.text((90 + bw/2 - 50, 800), "实拍原图", font=font(28), fill=SUB)
d.text((W - 90 - bw/2 - 70, 800), "美化建档后", font=font(28), fill=SUB)
step_badge(d, "② AI 美化建档")
im.save(OUT / "f3.png")

# ---------- 帧 4: 衣橱墙 ----------
im, d = base()
center_text(d, 80, "全部单品入库", font(52, 0))
center_text(d, 160, "自动识别分类 · 手动调类 · 随时补充", font(30), SUB)
wall = Image.open(ROOT / "美化单品预览墙.png").convert("RGB")
t = rounded(cover(wall, 860, 620))
shadow_paste(im, t, (W - 860) // 2, 240)
step_badge(d, "③ 衣橱建档")
im.save(OUT / "f4.png")

# ---------- 帧 5: 勾选搭配 ----------
im, d = base()
center_text(d, 80, "勾选单品  自由搭配", font(52, 0))
center_text(d, 160, "连衣裙 + 帽 + 耳环 + 鞋 + 包", font(30), SUB)
picks = ["item15.png", "item40.png", "item25.png", "item20.png", "item37.png"]
iw = 190
gap = 24
x0 = (W - (iw * len(picks) + gap * (len(picks) - 1))) / 2
for i, name in enumerate(picks):
    p = Image.open(ROOT / "items-beauty" / name).convert("RGBA")
    # 白卡
    card = Image.new("RGBA", (iw, 300), (255, 255, 255, 255))
    t = contain(p, iw - 16, 240)
    card.paste(t, ((iw - t.width) // 2, (250 - t.height) // 2), t)
    cd = ImageDraw.Draw(card)
    cx, cy = iw/2, 277
    cd.rounded_rectangle([cx - 24, cy - 15, cx + 24, cy + 15], 8, outline=ACCENT, width=3)
    cd.line([(cx - 10, cy), (cx - 3, cy + 7), (cx + 11, cy - 8)], fill=ACCENT, width=4, joint="curve")
    card = rounded(card, 20)
    shadow_paste(im, card, int(x0 + i * (iw + gap)), 320)
center_text(d, 720, "勾什么  搭什么", font(36), INK)
step_badge(d, "④ 勾选搭配")
im.save(OUT / "f5.png")

# ---------- 帧 6: 成片 ----------
im, d = base()
cardimg = Image.open(ROOT / "小红书卡-法式复古通勤.png").convert("RGB")
t = rounded(contain(cardimg, 560, 996), 20)
shadow_paste(im, t, (W - t.width) // 2 - 140, 42)
# 右侧文案
d.text((W - 380, 300), "一键生成", font=font(46, 0), fill=INK)
d.text((W - 380, 370), "小红书搭配卡", font=font(46, 0), fill=INK)
d.line([(W - 380, 450), (W - 200, 450)], fill=ACCENT, width=4)
d.text((W - 380, 490), "9:16 竖版 · 杂志拼贴", font=font(28), fill=SUB)
d.text((W - 380, 534), "柔和投影 · 微旋转", font=font(28), fill=SUB)
d.text((W - 380, 578), "直发小红书 / 公众号", font=font(28), fill=SUB)
step_badge(d, "⑤ 生成搭配卡")
im.save(OUT / "f6.png")

print("frames done:", sorted(p.name for p in OUT.glob("f*.png")))
