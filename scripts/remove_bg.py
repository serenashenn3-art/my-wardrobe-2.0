#!/usr/bin/env python3
"""remove_bg.py — 单品照片抠图,输出白底/透明底单品图.

优先使用 rembg(本地 AI 抠图,无需联网);未安装时给出安装指引并退出,
由 agent 走备选方案(见 references/style-guide.md「抠图备选」)。

用法:
    python3 remove_bg.py input.jpg                  # -> input_cutout.png (透明底)
    python3 remove_bg.py input.jpg --white          # -> 白底 PNG
    python3 remove_bg.py *.jpg -d cutouts/          # 批量输出到目录
"""

import argparse
import glob
import os
import sys
import traceback

try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


def process(src, dst, white=False, model="u2net"):
    from PIL import Image
    from rembg import new_session
    session = new_session(model)
    with open(src, "rb") as f:
        result = remove(f.read(), session=session)
    out_path = os.path.splitext(dst)[0] + ".png"
    with open(out_path, "wb") as f:
        f.write(result)
    if white:
        img = Image.open(out_path).convert("RGBA")
        base = Image.new("RGBA", img.size, (255, 255, 255, 255))
        base.alpha_composite(img)
        base.convert("RGB").save(out_path, "PNG")
    print(f"抠图完成: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="单品照片抠图(rembg)")
    ap.add_argument("inputs", nargs="+", help="图片路径或 glob 模式")
    ap.add_argument("-d", "--outdir", default=".", help="输出目录")
    ap.add_argument("--white", action="store_true", help="输出白底而非透明底")
    ap.add_argument("-m", "--model", default="u2net",
                    help="rembg 模型;默认 u2net(176MB),网络慢时用 u2netp(4.7MB)")
    args = ap.parse_args()

    if not HAS_REMBG:
        sys.exit(
            "未安装 rembg。安装: pip install rembg\n"
            "无法安装时,改用备选抠图方案(见 references/style-guide.md)。"
        )

    os.makedirs(args.outdir, exist_ok=True)
    files = []
    for pat in args.inputs:
        files.extend(glob.glob(pat) or [pat])

    # 批量处理: 单张异常不中断后续
    n_ok, n_fail = 0, 0
    for src in files:
        if not os.path.exists(src):
            print(f"[warn] 找不到 {src},跳过", file=sys.stderr)
            n_fail += 1
            continue
        dst = os.path.join(args.outdir, os.path.basename(src))
        try:
            process(src, dst, white=args.white, model=args.model)
            n_ok += 1
        except Exception as e:
            n_fail += 1
            print(f"[error] 抠图失败: {src}", file=sys.stderr)
            print(f"        原因: {e}", file=sys.stderr)
            if "--debug" in sys.argv:
                traceback.print_exc(file=sys.stderr)

    total = len(files)
    if n_fail > 0:
        print(f"\n批量抠图完成: {n_ok}/{total} 成功, {n_fail} 失败", file=sys.stderr)
    else:
        print(f"\n批量抠图完成: {n_ok}/{total} 全部成功")

    # 有失败时返回非零退出码, 方便脚本调用方检测
    if n_fail > 0 and n_ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
