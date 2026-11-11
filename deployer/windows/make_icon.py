#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成部署器图标 app.ico / app.png（锥形瓶 + 液体）

只用 Pillow，构建期运行一次即可；产物直接提交到仓库，避免构建 exe 时还要装图形库。

用法：python make_icon.py
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 512

TOP_COLOR = (99, 102, 241)      # indigo-500
BOTTOM_COLOR = (67, 56, 202)    # indigo-700
GLASS = (255, 255, 255, 255)
LIQUID = (34, 211, 238, 255)    # cyan-400
BUBBLE = (165, 243, 252, 255)   # cyan-200


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def gradient(size, top, bottom):
    img = Image.new("RGB", (1, size))
    pixels = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        pixels[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return img.resize((size, size), Image.BILINEAR)


def flask_art(size):
    """白色锥形瓶 + 青色液体的透明图层"""
    art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(art)

    # 以 512 为基准绘制，再按需缩放
    scale = size / 512.0

    def s(*values):
        return [v * scale for v in values]

    # 瓶身：颈部 + 梯形瓶体 + 圆底
    draw.polygon(s(216, 108, 296, 108, 296, 200, 372, 344, 140, 344), fill=GLASS)
    draw.rounded_rectangle(s(140, 300, 372, 408), radius=46 * scale, fill=GLASS)

    # 液体：贴着瓶底，左右各留一点玻璃边
    draw.rounded_rectangle(s(164, 330, 348, 392), radius=34 * scale, fill=LIQUID)

    # 气泡
    draw.ellipse(s(300, 236, 344, 280), fill=BUBBLE)
    draw.ellipse(s(238, 264, 268, 294), fill=BUBBLE)

    return art


def build(size=SIZE):
    base = gradient(size, TOP_COLOR, BOTTOM_COLOR).convert("RGBA")
    mask = rounded_mask(size, radius=int(size * 0.22))
    base.putalpha(mask)

    art = flask_art(size)
    base = Image.alpha_composite(base, art)

    # 顶部高光，避免纯色块显得闷
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(shine)
    d.ellipse([-size * 0.35, -size * 0.75, size * 1.35, size * 0.42],
              fill=(255, 255, 255, 26))
    base = Image.alpha_composite(base, Image.composite(
        shine, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))
    return base


def main():
    icon = build(SIZE)
    png_path = os.path.join(HERE, "app.png")
    ico_path = os.path.join(HERE, "app.ico")
    icon.save(png_path)
    icon.save(ico_path, format="ICO",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                     (64, 64), (128, 128), (256, 256)])
    print("生成 %s（%.1f KB）" % (png_path, os.path.getsize(png_path) / 1024))
    print("生成 %s（%.1f KB）" % (ico_path, os.path.getsize(ico_path) / 1024))

    # 顺带输出一张 40px 的预览，方便检查小尺寸下的辨识度
    icon.resize((40, 40), Image.LANCZOS).save(
        os.path.join(HERE, "app-preview-40.png"))


if __name__ == "__main__":
    main()
