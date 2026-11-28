"""定期タスクが Web 検索で見つけた記事を、その日の inbox の候補に足す（inbox はコミットしないので、手元だけ）。

本文は、実際に読んだページ（動画なら概要欄）の内容を、テキストファイルにして渡す。台本の事実は、この本文の範囲だけにする。

usage: python3 tools/add_candidate.py --channel summoners --url <URL> --title <題> --body-file <本文.txt>
                                      [--site <サイト名>] [--published YYYY-MM-DD] [--date YYYY-MM-DD] [--inbox inbox]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R


def main():
    a = sys.argv[1:]
    cid, url, title, bf = (R.arg(a, k) for k in ("--channel", "--url", "--title", "--body-file"))
    if not (cid and url and title and bf):
        print(__doc__); sys.exit(2)
    date = R.arg(a, "--date") or str(R.today_jst())
    path = os.path.join(R.arg(a, "--inbox", os.path.join(R.ROOT, "inbox")), date, f"{cid}.json")
    data = R.load_json(path, None)
    if data is None:
        print(f"{path} がない（先にニュース集めを動かす）"); sys.exit(1)
    body = open(bf, encoding="utf-8").read().strip()
    if len(body) < 120:
        print("本文が短すぎる（120 字以上。読んだページの中身を入れる）"); sys.exit(1)
    if any(c["url"] == url for c in data["candidates"]):
        print("もう候補にある"); return
    site = R.arg(a, "--site") or url.split("/")[2]
    data["candidates"].append({
        "title": title, "url": url, "summary": body[:400], "published": R.arg(a, "--published"), "source": site,
        "found_by": "web_search",
        "link": {"url": url, "title": title, "site": site, "description": body[:200], "image": None, "icon": None},
        "body": body[:6000],
    })
    R.save_json(path, data)
    print(f"足した：{title}（候補 {len(data['candidates'])} 本）")


if __name__ == "__main__":
    main()
