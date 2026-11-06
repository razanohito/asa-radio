"""チャンネルの仮キャスター（オリジナルキャラ）の差分画像を作る。

本番のキャラ画像に差し替えるまでのつなぎです。SVG で描いた絵を PNG にして、
  base.png          口を閉じて正面
  mouth_half.png    口・半開き（口のまわりだけ）
  mouth_open.png    口・開き
  smile_mouth.png   笑顔の口
  blink.png         目・閉じ（目のまわりだけ）
  half_blink.png    目・半目
を channels/<ID>/character/ に書き出し、character.json の位置（x, y）もそろえます。

usage: python3 tools/make_character.py [ID ...]   （省略すると、下の THEMES にある全チャンネル）
必要なもの：Pillow、resvg-py（pip install resvg-py）
"""
import io, json, os, sys
import resvg_py
from PIL import Image, ImageChops

W, H = 896, 768
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE = "#2a2233"

# チャンネルごとのキャラ（色と小物）。どれもこの道具で描いたオリジナルです
THEMES = {
    "ai": {   # アサヒ：紺の髪、オレンジの目、日の出の髪留め
        "name": "アサヒ", "bg": "#161a26",
        "skin": "#fde4d6", "skin_sh": "#f2c3b0", "hair": "#34406e", "hair_hi": "#4d5c96", "hair_sh": "#232c52",
        "iris": "#ff9d3c", "iris_d": "#c2571a", "jacket": "#2d3550", "jacket_sh": "#1f2539", "accent": "#ffd028", "headset": "#3fe0dc",
        "badge": "ON AIR", "long": False, "glasses": False,
        "accessory": '<circle cx="566" cy="196" r="15" fill="#ffd028"/><path d="M546,196 h40" stroke="#2d3550" stroke-width="3"/>',
    },
    "tech": {   # ミライ：深緑の髪、緑の目、めがね、回路の髪留め
        "name": "ミライ", "bg": "#121c1f",
        "skin": "#fbe3d4", "skin_sh": "#eec0ab", "hair": "#1f5a5e", "hair_hi": "#2f8189", "hair_sh": "#143c40",
        "iris": "#3fd9a0", "iris_d": "#16805c", "jacket": "#3a4152", "jacket_sh": "#282e3b", "accent": "#3fe0dc", "headset": "#9cff57",
        "badge": "TECH", "long": False, "glasses": True,
        "accessory": '<rect x="548" y="182" width="34" height="26" rx="5" fill="#9cff57"/><path d="M556,182v-8M566,182v-8M576,182v-8M556,208v8M566,208v8M576,208v8" stroke="#9cff57" stroke-width="3"/><rect x="556" y="190" width="18" height="10" rx="2" fill="#143c40"/>',
    },
    "summoners": {   # ルナ：紫の長い髪、金の目、星のティアラ、マント
        "name": "ルナ", "bg": "#1c1428",
        "skin": "#fde6da", "skin_sh": "#f0c4b4", "hair": "#6b45a8", "hair_hi": "#8f6ad0", "hair_sh": "#47297a",
        "iris": "#ffc93c", "iris_d": "#c27a12", "jacket": "#7a1f3d", "jacket_sh": "#56142a", "accent": "#ffc93c", "headset": "#ff7ad9",
        "badge": "SUMMON", "long": True, "glasses": False,
        "accessory": '<path d="M392,150 Q448,128 504,150" fill="none" stroke="#ffc93c" stroke-width="6" stroke-linecap="round"/><path d="M448,112 l9,20 22,2 -17,14 5,21 -19,-11 -19,11 5,-21 -17,-14 22,-2z" fill="#ffc93c" stroke="#c27a12" stroke-width="2"/><circle cx="448" cy="140" r="5" fill="#ff7ad9"/>',
    },
}


def eyes(T, state):
    """state: open / half / closed"""
    out = []
    for side in (-1, 1):
        cx, cy = 448 + side * 70, 300
        if state == "closed":
            out.append(f'<path d="M{cx-34},{cy+4} Q{cx},{cy+22} {cx+34},{cy+4}" fill="none" stroke="{LINE}" stroke-width="6" stroke-linecap="round"/>')
            out.append(f'<path d="M{cx+side*30},{cy+6} l{side*10},-6" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/>')
            continue
        eye = (f'<ellipse cx="{cx}" cy="{cy}" rx="33" ry="40" fill="#ffffff"/>'
               f'<ellipse cx="{cx}" cy="{cy+4}" rx="25" ry="33" fill="url(#iris)"/>'
               f'<ellipse cx="{cx}" cy="{cy+8}" rx="11" ry="15" fill="{T["iris_d"]}"/>'
               f'<ellipse cx="{cx-9}" cy="{cy-10}" rx="9" ry="11" fill="#ffffff"/>'
               f'<circle cx="{cx+10}" cy="{cy+17}" r="4.5" fill="#ffffff" opacity=".85"/>')
        clip = f"eyeclip{side}"
        out.append(f'<clipPath id="{clip}"><ellipse cx="{cx}" cy="{cy}" rx="34" ry="41"/></clipPath>')
        out.append(f'<g clip-path="url(#{clip})">{eye}')
        if state == "half":
            out.append(f'<rect x="{cx-40}" y="{cy-50}" width="80" height="48" fill="{T["skin"]}"/>')
            out.append(f'</g><path d="M{cx-36},{cy-2} Q{cx},{cy-10} {cx+36},{cy-2}" fill="none" stroke="{LINE}" stroke-width="7" stroke-linecap="round"/>')
        else:
            out.append('</g>')
            out.append(f'<path d="M{cx-37},{cy-18} Q{cx},{cy-50} {cx+37},{cy-18}" fill="none" stroke="{LINE}" stroke-width="7" stroke-linecap="round"/>')
            out.append(f'<path d="M{cx+side*34},{cy-20} l{side*11},-9" stroke="{LINE}" stroke-width="5" stroke-linecap="round"/>')
    return "".join(out)


def mouth(state):
    cx, cy = 448, 398
    if state == "closed":
        return f'<path d="M{cx-14},{cy} Q{cx},{cy+9} {cx+14},{cy}" fill="none" stroke="{LINE}" stroke-width="4.5" stroke-linecap="round"/>'
    if state == "half":
        return (f'<path d="M{cx-15},{cy-3} Q{cx},{cy+20} {cx+15},{cy-3} Q{cx},{cy+1} {cx-15},{cy-3}Z" fill="#a8334a" stroke="{LINE}" stroke-width="3.5" stroke-linejoin="round"/>'
                f'<ellipse cx="{cx}" cy="{cy+8}" rx="6" ry="3" fill="#f07b8a"/>')
    if state == "open":
        return (f'<path d="M{cx-18},{cy-6} Q{cx},{cy+34} {cx+18},{cy-6} Q{cx},{cy-2} {cx-18},{cy-6}Z" fill="#a8334a" stroke="{LINE}" stroke-width="3.5" stroke-linejoin="round"/>'
                f'<ellipse cx="{cx}" cy="{cy+15}" rx="9" ry="5" fill="#f07b8a"/>')
    return (f'<path d="M{cx-24},{cy-6} Q{cx},{cy+28} {cx+24},{cy-6} Q{cx},{cy+2} {cx-24},{cy-6}Z" fill="#a8334a" stroke="{LINE}" stroke-width="3.5" stroke-linejoin="round"/>'
            f'<path d="M{cx-18},{cy-3} Q{cx},{cy+3} {cx+18},{cy-3} L{cx+14},{cy+2} Q{cx},{cy+6} {cx-14},{cy+2}Z" fill="#ffffff"/>'
            f'<ellipse cx="{cx}" cy="{cy+12}" rx="8" ry="4" fill="#f07b8a"/>')


def glasses():
    g = ""
    for side in (-1, 1):
        cx = 448 + side * 70
        g += f'<rect x="{cx-46}" y="258" width="92" height="82" rx="22" fill="#bfe9ff" fill-opacity=".12" stroke="#20242e" stroke-width="6"/>'
    return g + '<path d="M494,290 Q448,276 402,290" fill="none" stroke="#20242e" stroke-width="6"/>'


def svg(T, eye_state="open", mouth_state="closed"):
    back = ("M262,300 Q256,140 448,118 Q640,140 634,300 L666,700 Q610,740 566,690 L548,380 L348,380 L330,690 Q286,740 230,700 Z" if T["long"]
            else "M268,300 Q262,140 448,118 Q634,140 628,300 L640,520 Q600,560 556,520 L548,380 L348,380 L340,520 Q296,560 256,520 Z")
    cape = (f'<path d="M150,768 Q170,610 290,566 L330,600 Q250,650 236,768 Z M746,768 Q726,610 606,566 L566,600 Q646,650 660,768 Z" fill="{T["jacket_sh"]}"/>'
            f'<path d="M300,560 Q448,600 596,560" fill="none" stroke="{T["accent"]}" stroke-width="6"/>') if T["long"] else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
 <linearGradient id="iris" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["iris_d"]}"/><stop offset=".55" stop-color="{T["iris"]}"/><stop offset="1" stop-color="#fff1c2"/></linearGradient>
 <linearGradient id="hair" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["hair_hi"]}"/><stop offset="1" stop-color="{T["hair"]}"/></linearGradient>
</defs>
<path d="{back}" fill="{T["hair_sh"]}"/>
<path d="M180,768 Q190,600 300,560 L400,530 L496,530 L596,560 Q706,600 716,768 Z" fill="{T["jacket"]}"/>
<path d="M300,560 L400,530 L448,640 Z" fill="{T["jacket_sh"]}"/>
<path d="M596,560 L496,530 L448,640 Z" fill="{T["jacket_sh"]}"/>
{cape}
<path d="M404,520 L448,640 L492,520 Z" fill="#f6f4fb"/>
<path d="M448,560 L418,540 L414,584 Z M448,560 L478,540 L482,584 Z" fill="{T["accent"]}"/>
<circle cx="448" cy="562" r="9" fill="{T["iris_d"]}"/>
<rect x="556" y="600" width="72" height="20" rx="6" fill="{T["accent"]}"/>
<text x="592" y="615" font-family="sans-serif" font-size="13" font-weight="700" fill="{T["jacket"]}" text-anchor="middle">{T["badge"]}</text>
<path d="M410,440 L410,530 Q448,552 486,530 L486,440 Z" fill="{T["skin_sh"]}"/>
<path d="M300,280 Q300,450 448,480 Q596,450 596,280 Q596,150 448,150 Q300,150 300,280 Z" fill="{T["skin"]}"/>
<ellipse cx="368" cy="372" rx="26" ry="12" fill="#ff8f8f" opacity=".35"/>
<ellipse cx="528" cy="372" rx="26" ry="12" fill="#ff8f8f" opacity=".35"/>
{eyes(T, eye_state)}
{glasses() if T["glasses"] else ""}
<path d="M446,352 l-4,10 l6,0" fill="none" stroke="{T["skin_sh"]}" stroke-width="3" stroke-linecap="round"/>
{mouth(mouth_state)}
<path d="M300,250 Q280,360 300,470 Q318,440 326,380 Q330,300 320,250 Z" fill="url(#hair)"/>
<path d="M596,250 Q616,360 596,470 Q578,440 570,380 Q566,300 576,250 Z" fill="url(#hair)"/>
<path d="M286,300 Q270,130 448,120 Q626,130 610,300 Q590,230 560,212 Q556,250 538,262 Q526,220 498,206 Q490,240 470,252 Q462,214 440,204 Q420,236 396,246 Q396,214 380,206 Q356,236 330,250 Q322,226 318,214 Q296,250 286,300 Z" fill="url(#hair)"/>
<path d="M360,160 Q420,140 470,150" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity=".25"/>
<path d="M450,124 Q440,70 480,58 Q462,80 470,122 Z" fill="{T["hair"]}"/>
{T["accessory"]}
<path d="M278,290 Q272,96 448,92 Q624,96 618,290" fill="none" stroke="#1b1f2c" stroke-width="13" stroke-linecap="round"/>
<rect x="262" y="262" width="40" height="78" rx="18" fill="#1b1f2c"/>
<rect x="270" y="276" width="10" height="50" rx="5" fill="{T["headset"]}"/>
<rect x="594" y="262" width="40" height="78" rx="18" fill="#1b1f2c"/>
<path d="M290,336 Q300,430 360,446" fill="none" stroke="#1b1f2c" stroke-width="7" stroke-linecap="round"/>
<ellipse cx="368" cy="447" rx="13" ry="10" fill="#1b1f2c"/>
<ellipse cx="368" cy="446" rx="6" ry="4" fill="{T["headset"]}"/>
</svg>'''


def render(T, **kw):
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg(T, **kw)))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def crop_part(base, variants, pad=6):
    """variants の差分を全部ふくむ枠で、それぞれを切り出す（同じ x, y にそろえる）"""
    box = None
    for v in variants:
        b = ImageChops.difference(base, v).getbbox(alpha_only=False)
        if b: box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    x0, y0, x1, y1 = max(0, box[0] - pad), max(0, box[1] - pad), min(W, box[2] + pad), min(H, box[3] + pad)
    return (x0, y0), [v.crop((x0, y0, x1, y1)) for v in variants]


def make(cid):
    T = THEMES[cid]
    out = os.path.join(ROOT, "channels", cid, "character")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".png"): os.remove(os.path.join(out, f))
    base = render(T)
    base.save(os.path.join(out, "base.png"))
    mouths = {"mouth_half": render(T, mouth_state="half"), "mouth_open": render(T, mouth_state="open"), "smile_mouth": render(T, mouth_state="smile")}
    eyes_ = {"blink": render(T, eye_state="closed"), "half_blink": render(T, eye_state="half")}
    parts = {}
    for group in (mouths, eyes_):
        (x, y), imgs = crop_part(base, list(group.values()))
        for name, img in zip(group, imgs):
            img.save(os.path.join(out, f"{name}.png"))
            parts[name] = {"src": f"{name}.png", "x": x, "y": y}
    pack = {
        "format": "myradio/character-1", "type": "sprites", "size": [W, H], "background": T["bg"],
        "base": "base.png", "parts": parts,
        "mouth": {"1": "mouth_half", "2": "mouth_open"},
        "eye": {"blink": "blink", "half": "half_blink"},
        "expressions": {"smile": {"mouth": "smile_mouth"}},
        "note": f"仮のオリジナルキャラ「{T['name']}」（tools/make_character.py で生成）。本番の絵に替えるときは base.png と差分画像、この JSON の x, y を書き換える",
    }
    with open(os.path.join(out, "character.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    print(f"{cid}（{T['name']}）:", ", ".join(sorted(os.listdir(out))))


if __name__ == "__main__":
    for cid in sys.argv[1:] or THEMES:
        make(cid)
