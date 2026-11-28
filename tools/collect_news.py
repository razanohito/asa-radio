"""毎朝のニュース集め：各チャンネルの候補記事を集め、記事のページ（OGP と本文）も読んで、inbox/<日付>/<ID>.json に書く。

台本を書く人（Claude の定期タスク、または tools/make_script.py）は、この inbox だけを見て台本を書けます。
GitHub Actions（.github/workflows/collect.yml）が毎朝動かし、inbox ブランチに置きます。

usage: python3 tools/collect_news.py [--date YYYY-MM-DD] [--channels ai,tech] [--out inbox] [--max 30]
"""
import datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R


def collect_channel(cid, date, limit):
    st = R.station(cid); cfg = st.get("news") or {}
    cands = R.collect(cfg.get("feeds", []), hours=int(cfg.get("hours", 36)), keywords=cfg.get("keywords"), exclude=cfg.get("exclude"))
    used = R.used_urls(R.chan_dir(cid))
    n_all = len(cands)
    cands = [c for c in cands if c["url"].split("?")[0].rstrip("/") not in used]
    print(f"[{cid}] 候補 {n_all} 本（放送済みを除いて {len(cands)} 本）")
    out = []
    for c in cands[:limit * 2]:          # 読めない記事があるので多めに当たる
        link, body = R.page_info(c["url"])
        if "status" in link:
            print(f"  読めない {link.get('status')} {c['url'][:100]}"); continue
        # 動画や SNS の投稿はページに本文が少ない。フィードの説明文（YouTube の概要欄など）を本文の代わりにする
        if len(body) < 200 and len(c.get("summary", "")) >= 120:
            body = c["summary"]
        if len(body) < 200:
            print(f"  本文が短い {len(body)} {c['url'][:100]}"); continue
        out.append({**c, "link": link, "body": body[:6000]})
        if len(out) >= limit: break
    keep = ("topic", "count", "min", "caster_name", "persona", "tone", "farewell", "length", "pick_rules", "write_rules")
    return {"date": str(date), "channel": cid, "name": st.get("name"), "news": {k: cfg[k] for k in keep if k in cfg},
            "candidates": out}


def main():
    a = sys.argv[1:]
    date = datetime.date.fromisoformat(R.arg(a, "--date")) if "--date" in a else R.today_jst()
    ids = [c for c in R.arg(a, "--channels", "").split(",") if c] or R.channels()
    out = R.arg(a, "--out", os.path.join(R.ROOT, "inbox")); limit = int(R.arg(a, "--max", "30"))
    for cid in ids:
        if R.station(cid).get("paused"): continue
        print(f"[{cid}]")
        data = collect_channel(cid, date, limit)
        R.save_json(os.path.join(out, str(date), f"{cid}.json"), data)
        print(f"[{cid}] 読めた記事 {len(data['candidates'])} 本")


if __name__ == "__main__":
    main()
