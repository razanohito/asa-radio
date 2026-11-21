"""手で（または Claude が）書いた台本の下書きを確かめて、チャンネルの台本として保存する。

下書き（JSON）は {"title", "opening", "news": [{"label", "points", "details", "lines", "url"}], "closing", "highlight"}。
news[].url は inbox の候補記事の URL をそのまま使う。リンクカード（link）は inbox から自動で付ける。

usage: python3 tools/save_script.py --channel ai --draft 下書き.json [--date YYYY-MM-DD] [--inbox inbox] [--force]
問題があれば、直すべき点を表示して終了コード 1（保存しない）。
"""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R


def main():
    a = sys.argv[1:]
    cid = R.arg(a, "--channel") or sys.exit(__doc__)
    draft = R.load_json(R.arg(a, "--draft") or sys.exit(__doc__))
    date = datetime.date.fromisoformat(R.arg(a, "--date")) if "--date" in a else R.today_jst()
    inbox = R.load_json(os.path.join(R.arg(a, "--inbox", os.path.join(R.ROOT, "inbox")), str(date), f"{cid}.json"), {}) or {}
    by_url = {c["url"]: c for c in inbox.get("candidates", [])}
    min_news = int((inbox.get("news") or {}).get("min", 1))
    errs = R.check_script(draft, set(by_url) or None, min_news) if isinstance(draft, dict) else ["JSON がオブジェクトではない"]
    if errs:
        print("直すべき点：\n- " + "\n- ".join(errs)); sys.exit(1)
    out = os.path.join(R.chan_dir(cid), "episodes", f"{date}-ja.json")
    if os.path.exists(out) and "--force" not in a:
        print(f"{out} はもうあります（上書きするなら --force）"); sys.exit(1)
    for n in draft["news"]:
        c = by_url.get(n["url"])
        if c: n["link"] = c["link"]
    ep = {"format": "monoradio/news-1", "date": str(date), "lang": "ja", "title": draft["title"], "opening": draft["opening"],
          "news": draft["news"], "closing": draft["closing"], **({"highlight": draft["highlight"]} if "highlight" in draft else {})}
    R.save_json(out, ep)
    print(f"保存：{out}（{len(ep['news'])} 本）「{ep['title']}」")


if __name__ == "__main__":
    main()
