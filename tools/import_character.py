"""手持ちの立ち絵（口の開け閉め・表情の差分 PNG）を、チャンネルのキャスターに取り込む。

ゆっくり動画のキャラ素材のような「表情ごとに 1 枚の絵」の形から、プレーヤー用の
  base.png（口を閉じた絵）＋ 変わった範囲だけの小さな差分画像 ＋ character.json
を作ります。絵は 896×768 の枠に、下ぞろえ・中央で収めます（縮小のみ。絵そのものは描き変えません）。

usage:
  python3 tools/import_character.py CHANNEL --closed 口閉じ.png --open 口開き.png
      [--half 口半開き.png] [--smile 笑顔.png] [--blink 目閉じ.png] [--half-blink 半目.png]
      [--bg "#1c1428"] [--height 0.98] [--name 名前] [--credit "立ち絵：…"]
  --height  枠の高さに対する絵の高さ（既定 0.98）
  --half    なければ、口半開きにも口開きの絵を使う
  --smile   締めの笑顔（口閉じの笑顔の絵がよい）
  --blink   なければ、まばたきはしない
  --mouth-box x0,y0,x1,y1   口の差分を切り出す範囲（896×768 の枠での座標）。省略すると自動で探す。
                            AI で描いた差分のように顔全体が少しずつ違う絵では、指定したほうがきれい
  --eye-box   x0,y0,x1,y1   目の差分の範囲（同上）
  --loose   差分の絵が元の絵と大きさ・位置までちがうとき（別に描き直してもらった絵など）、大きさも合わせて重ねる
"""
import json, os, sys
from PIL import Image, ImageChops

W, H = 896, 768
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def place(path, height, box=None):
    """絵を W×H の透明な枠に、下ぞろえ・中央で置く。box を渡すと、その切り取り範囲と縮尺を使う（差分の絵を元の絵にそろえるため）"""
    im = Image.open(path).convert("RGBA")
    box = box or im.getbbox() or (0, 0, im.width, im.height)
    im = im.crop(box)                                  # 周りの透明な余白を除く
    s = min(H * height / im.height, W / im.width)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(im, ((W - im.width) // 2, H - im.height))
    out.info["box"] = box
    return out


def align(base, v, reach=12, scales=(1.0,)):
    """差分の絵 v を、元の絵 base にいちばん重なる位置・大きさにそろえる（AI で描き直した絵は数ピクセルずれることがある）"""
    import numpy as np
    def gray(im, k=4):
        bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(im)
        return np.asarray(bg.convert("L").resize((W // k, H // k), Image.BILINEAR), dtype=np.float32)
    def warp(s, dx, dy):
        w, h = round(W * s), round(H * s)
        out = Image.new("RGBA", (W, H)); out.alpha_composite(v.resize((w, h), Image.LANCZOS), (0, 0)) if False else None
        sv = v.resize((w, h), Image.BILINEAR)
        out.paste(sv, ((W - w) // 2 + dx, (H - h) + dy), sv)
        return out
    B = gray(base); best = (1e9, 1.0, 0, 0)
    for s in scales:                                   # 粗く（1/4 の大きさで）探す
        for dx in range(-reach, reach + 1, 4):
            for dy in range(-reach, reach + 1, 4):
                e = np.abs(gray(warp(s, dx, dy))[5:-5, 5:-5] - B[5:-5, 5:-5]).mean()
                if e < best[0]: best = (e, s, dx, dy)
    _, s0, x0, y0 = best
    B2 = gray(base, 2)
    for dx in range(x0 - 4, x0 + 5, 2):                 # 細かく探す
        for dy in range(y0 - 4, y0 + 5, 2):
            e = np.abs(gray(warp(s0, dx, dy), 2)[10:-10, 10:-10] - B2[10:-10, 10:-10]).mean()
            if e < best[0] or (dx, dy) == (x0, y0): best = min(best, (e, s0, dx, dy))
    _, s, dx, dy = best
    w, h = round(W * s), round(H * s)
    out = Image.new("RGBA", (W, H)); sv = v.resize((w, h), Image.LANCZOS)
    out.paste(sv, ((W - w) // 2 + dx, (H - h) + dy), sv)
    return out


def diff_box(base, v, focus):
    """base と v で絵が変わった範囲。focus なら、いちばん変化の集まった塊だけ（AI で描き直した差分は全体が少しずつずれるため）"""
    import numpy as np
    d = np.asarray(ImageChops.difference(base, v).convert("L"), dtype=np.int32)
    m = d > 40
    if not m.any(): return None
    if not focus:
        ys, xs = np.nonzero(m); return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    # 線のわずかなずれは細いので、ぼかすと消える。口のように面で変わった所だけが濃く残る
    from PIL import ImageFilter
    blur = np.asarray(Image.fromarray(np.clip(d, 0, 255).astype("uint8")).filter(ImageFilter.BoxBlur(7)), dtype=np.int32)
    peak = np.unravel_index(blur.argmax(), blur.shape)
    keep = blur > max(25, blur.max() * 0.3)
    # 一番濃い点からつながっている範囲だけ（目など、離れた別の変化は含めない）
    from collections import deque
    seen = np.zeros_like(keep); seen[peak] = True; q = deque([peak]); ys, xs = [peak[0]], [peak[1]]
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < H and 0 <= nx < W and keep[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx)); ys.append(ny); xs.append(nx)
    return (min(xs) - 6, min(ys) - 6, max(xs) + 7, max(ys) + 7)


def crop_part(base, variants, focus=True, pad=10, box=None):
    for v in variants if box is None else []:
        b = diff_box(base, v, focus)
        if b: box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    if box is None: raise SystemExit("差分がありません（同じ絵どうしです）")
    box = tuple(int(b) for b in box)
    x0, y0, x1, y1 = max(0, box[0] - pad), max(0, box[1] - pad), min(W, box[2] + pad), min(H, box[3] + pad)
    # 切り口がなじむよう、ふちの pad ぶんを透明に向けてぼかす
    from PIL import ImageDraw, ImageFilter
    fw, fh = x1 - x0, y1 - y0
    feather = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(feather).rectangle([pad // 2, pad // 2, fw - pad // 2, fh - pad // 2], fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(pad / 3))
    out = []
    for v in variants:
        c = v.crop((x0, y0, x1, y1))
        a = ImageChops.multiply(c.getchannel("A"), feather)
        # ふちでは base の色を下に敷いてから重ねる（透明な部分で本体が欠けないように）
        under = base.crop((x0, y0, x1, y1)); under.alpha_composite(Image.merge("RGBA", (*c.split()[:3], a)))
        out.append(under)
    return (int(x0), int(y0)), out


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"): sys.exit(__doc__)
    cid = sys.argv[1]
    height = float(arg("--height", "0.98"))
    out = os.path.join(ROOT, "channels", cid, "character")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".png"): os.remove(os.path.join(out, f))

    base = place(arg("--closed") or sys.exit("--closed が要ります"), height)
    base.save(os.path.join(out, "base.png"), optimize=True)
    parts, mouth_files = {}, {"mouth_open": arg("--open") or sys.exit("--open が要ります")}
    if arg("--half"): mouth_files["mouth_half"] = arg("--half")
    smile_files = {"smile_mouth": arg("--smile")} if arg("--smile") else {}
    eye_files = {k: arg(f) for k, f in (("blink", "--blink"), ("half_blink", "--half-blink")) if arg(f)}
    for group, focus in ((mouth_files, True), (smile_files, False), (eye_files, True)):
        if not group: continue
        if arg("--loose"):   # 別に描き直された絵（大きさや位置がちがう）：大きさも合わせて探す
            imgs = [align(base, place(p, height), reach=60, scales=[x / 100 for x in range(85, 116, 3)]) for p in group.values()]
        else:
            imgs = [align(base, place(p, height, base.info["box"])) for p in group.values()]
        manual = arg("--mouth-box") if group is mouth_files else arg("--eye-box") if group is eye_files else None
        (x, y), crops = crop_part(base, imgs, focus, box=tuple(map(int, manual.split(","))) if manual else None)
        for name, img in zip(group, crops):
            img.save(os.path.join(out, f"{name}.png"), optimize=True)
            parts[name] = {"src": f"{name}.png", "x": x, "y": y}

    pack = {"format": "myradio/character-1", "type": "sprites", "size": [W, H], "background": arg("--bg", "#161a26"),
            "base": "base.png", "parts": parts,
            "mouth": {"1": "mouth_half" if "mouth_half" in parts else "mouth_open", "2": "mouth_open"}}
    if "blink" in parts: pack["eye"] = {"blink": "blink", **({"half": "half_blink"} if "half_blink" in parts else {})}
    if "smile_mouth" in parts: pack["expressions"] = {"smile": {"mouth": "smile_mouth"}}
    pack["note"] = f"「{arg('--name', cid)}」の立ち絵を tools/import_character.py で取り込み" + (f"（{arg('--credit')}）" if arg("--credit") else "")
    with open(os.path.join(out, "character.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)) // 1024
    print(f"{cid}: {', '.join(sorted(os.listdir(out)))}（{size} KB）")


if __name__ == "__main__":
    main()
