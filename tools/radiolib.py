"""あさAIラジオの自動放送で使う共通の部品（ニュース集め・ページ読み・台本の確認）。

外部ライブラリは使いません（Python 3.10 以上の標準ライブラリだけ）。
"""
import datetime, html, json, os, re, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = datetime.timezone(datetime.timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; myradio-station/1.0; +https://github.com/monoradio102/myradio)"
WEEK = "月火水木金土日"


def today_jst():
    return datetime.datetime.now(JST).date()


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data, indent=1):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent); f.write("\n")
    os.replace(tmp, path)


def station():
    return load_json(os.path.join(ROOT, "station.json"))


def http_get(url, timeout=20, limit=3_000_000):
    """(最終URL, ステータス, 本文の文字列)。失敗したら (url, ステータスか None, '')"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(limit)
            cs = r.headers.get_content_charset()
            if not cs:
                m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:4000], re.I) or re.search(rb'encoding=["\']([\w-]+)', raw[:200])
                cs = m.group(1).decode() if m else "utf-8"
            try: text = raw.decode(cs, "replace")
            except LookupError: text = raw.decode("utf-8", "replace")
            return r.geturl(), r.status, text
    except urllib.error.HTTPError as e:
        return url, e.code, ""
    except Exception:
        return url, None, ""


# ---------------- フィード ----------------

def _txt(el):
    return "" if el is None else html.unescape(re.sub(r"<[^>]+>", " ", "".join(el.itertext()))).strip()


def _date(s):
    if not s: return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try: d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def parse_feed(xml_text, feed_url=""):
    """RSS 2.0 / RSS 1.0 (RDF) / Atom の記事を [{title, url, summary, published, source}] で返す"""
    xml_text = re.sub(r"^[^<]+", "", xml_text)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = []
    strip = lambda t: t.split("}", 1)[-1]
    source = ""
    for el in root.iter():
        if strip(el.tag) == "title": source = _txt(el); break
    for el in root.iter():
        tag = strip(el.tag)
        if tag not in ("item", "entry"): continue
        f = {strip(c.tag): c for c in el}
        title = _txt(f.get("title"))
        link = ""
        if "link" in f:
            link = f["link"].get("href") or _txt(f["link"])
            for c in el:   # Atom: rel=alternate を優先
                if strip(c.tag) == "link" and c.get("rel", "alternate") == "alternate" and c.get("href"):
                    link = c.get("href"); break
        summary = _txt(next((f[k] for k in ("description", "summary", "content", "encoded") if k in f), None))
        pub = None
        for k in ("pubDate", "published", "updated", "date", "issued"):
            if k in f: pub = _date(_txt(f[k])); break
        if title and link.startswith("http"):
            items.append({"title": title, "url": link.strip(), "summary": summary[:400], "published": pub.isoformat() if pub else None, "source": source or urllib.parse.urlparse(feed_url).netloc})
    return items


def collect(feeds, hours=36, now=None):
    """フィードから直近 hours 時間の記事を集める（URL と題で重複を除く）"""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    seen, out = set(), []
    for url in feeds:
        _, status, text = http_get(url)
        got = parse_feed(text, url) if text else []
        print(f"  feed {status} {len(got):3d} {url}")
        for it in got:
            if it["published"]:
                age = now - datetime.datetime.fromisoformat(it["published"])
                if age > datetime.timedelta(hours=hours) or age < datetime.timedelta(hours=-6): continue
            key = (it["url"].split("?")[0], re.sub(r"\W", "", it["title"])[:40])
            if key[0] in seen or key[1] in seen: continue
            seen.update(key); out.append(it)
    return out


# ---------------- 記事ページ（OGP と本文） ----------------

class _Page(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "button"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.icons, self.title, self.paras = {}, [], "", []
        self._skip, self._in_title, self._buf, self._in_p = 0, False, [], 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k and a.get("content") and k not in self.meta: self.meta[k] = a["content"].strip()
        elif tag == "link" and "icon" in a.get("rel", "").lower() and a.get("href"):
            self.icons.append((a.get("rel", ""), a.get("sizes", ""), a["href"]))
        elif tag == "title": self._in_title = True
        elif tag in self.SKIP: self._skip += 1
        elif tag in ("p", "h2", "h3", "li") and not self._skip: self._in_p += 1; self._buf = []

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        elif tag in self.SKIP and self._skip: self._skip -= 1
        elif tag in ("p", "h2", "h3", "li") and self._in_p:
            self._in_p -= 1
            t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(t) >= 20: self.paras.append(t)
            self._buf = []

    def handle_data(self, data):
        if self._in_title: self.title += data
        elif self._in_p and not self._skip: self._buf.append(data)


def page_info(url):
    """記事のページを読んで、リンクカード（link）と本文の抜き出しを返す"""
    final, status, text = http_get(url)
    if status != 200 or not text:
        return {"url": url, "status": status, "error": "HTTPError" if status else "Unreachable"}, ""
    p = _Page()
    try: p.feed(text)
    except Exception: pass
    m = p.meta
    abs_ = lambda u: urllib.parse.urljoin(final, u) if u else None
    icon = None
    if p.icons:
        apple = [i for i in p.icons if "apple" in i[0].lower()]
        icon = abs_((apple or p.icons)[0][2])
    link = {
        "url": final,
        "title": html.unescape(m.get("og:title") or m.get("twitter:title") or p.title.strip())[:200],
        "site": html.unescape(m.get("og:site_name") or urllib.parse.urlparse(final).netloc),
        "description": html.unescape(m.get("og:description") or m.get("description") or m.get("twitter:description") or "")[:300],
        "image": abs_(m.get("og:image") or m.get("og:image:url") or m.get("twitter:image")),
        "icon": icon,
    }
    body = "\n".join(p.paras)
    return link, body[:6000]


# ---------------- 台本の確認 ----------------

def _line_ok(x):
    return isinstance(x, dict) and isinstance(x.get("say"), str) and isinstance(x.get("show"), str) and x["say"].strip() and x["show"].strip()


def check_script(ep, allowed_urls=None):
    """台本 JSON の形を確かめる。おかしいところを文字列の並びで返す（空なら OK）"""
    errs = []
    for k in ("title", "opening", "news", "closing"):
        if k not in ep: errs.append(f"{k} がない")
    if errs: return errs
    if not isinstance(ep["title"], str) or not ep["title"].strip(): errs.append("title が空")
    for part in ("opening", "closing"):
        if not isinstance(ep[part], list) or not ep[part]: errs.append(f"{part} が空"); continue
        for i, x in enumerate(ep[part]):
            if not _line_ok(x): errs.append(f"{part}[{i}] に say と show がない")
    if not isinstance(ep["news"], list) or not 2 <= len(ep["news"]) <= 7: errs.append("news は 2〜7 本")
    else:
        for j, n in enumerate(ep["news"]):
            w = f"news[{j}]"
            for k in ("label", "points", "lines", "url"):
                if k not in n: errs.append(f"{w}.{k} がない")
            if not isinstance(n.get("points"), list) or not n.get("points"): errs.append(f"{w}.points が空")
            if not isinstance(n.get("lines"), list) or not n.get("lines"): errs.append(f"{w}.lines が空")
            else:
                for i, x in enumerate(n["lines"]):
                    if not _line_ok(x): errs.append(f"{w}.lines[{i}] に say と show がない")
            d = n.get("details")
            if d is not None and (not isinstance(d, list) or len(d) != len(n.get("points") or [])): errs.append(f"{w}.details は points と同じ数")
            if allowed_urls is not None and n.get("url") not in allowed_urls: errs.append(f"{w}.url が渡した記事の URL ではない: {n.get('url')}")
    for part in ("opening", "closing"):
        for x in ep.get(part, []):
            if _line_ok(x) and re.search(r"[A-Za-z]{2,}", x["say"]): errs.append(f"{part} の say に英字が残っている: {x['say']}")
    for j, n in enumerate(ep.get("news", []) if isinstance(ep.get("news"), list) else []):
        for x in n.get("lines", []) if isinstance(n.get("lines"), list) else []:
            if _line_ok(x) and re.search(r"[A-Za-z]{2,}", x["say"]): errs.append(f"news[{j}] の say に英字が残っている: {x['say']}")
    h = ep.get("highlight")
    if h is not None and not (isinstance(h, int) and 0 <= h < len(ep.get("news", []))): errs.append("highlight の番号がおかしい")
    return errs


def date_words(d):
    """台本の読み上げ用・字幕用の日付"""
    return f"{d.month}月{d.day}日{WEEK[d.weekday()]}曜日"
