"""サイト全体（複数チャンネル）の下ごしらえ。

usage:
  python3 tools/site.py prepare DIR   公開用のフォルダ DIR の中で、各チャンネルに player.html を index.html として置き、
                                      station.json の url・repo を channels.json の site から決めて書く（main は書き換えない）
  python3 tools/site.py local         手元で見るために、各チャンネルに player.html を index.html として置く（git には入れない）
  python3 tools/site.py set-url URL REPO  channels.json の site.url と site.repo を書く（GitHub Actions の初回に使う）
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R


def place_players(root):
    for cid in R.channels():
        d = os.path.join(root, "channels", cid)
        if os.path.exists(os.path.join(d, "station.json")):
            shutil.copyfile(os.path.join(R.ROOT, "player.html"), os.path.join(d, "index.html"))


def prepare(root):
    place_players(root)
    site = R.site()
    base, repo = (site.get("url") or "").rstrip("/"), site.get("repo") or ""
    for cid in R.channels():
        p = os.path.join(root, "channels", cid, "station.json")
        st = R.load_json(p)
        if base: st["url"] = f"{base}/channels/{cid}/"
        if repo: st["repo"] = repo
        R.save_json(p, st)
    print(f"チャンネル {len(R.channels())} 個を用意（{base or '公開先 URL 未設定'}）")


def main():
    a = sys.argv[1:]
    if a[:1] == ["prepare"]: prepare(a[1])
    elif a[:1] == ["local"]: place_players(R.ROOT); print("各チャンネルに index.html を置きました")
    elif a[:1] == ["set-url"]:
        p = os.path.join(R.ROOT, "channels.json"); c = R.load_json(p)
        c["site"]["url"], c["site"]["repo"] = a[1], a[2]
        R.save_json(p, c); print("site:", a[1])
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main()
