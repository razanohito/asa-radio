"""声がまだない最近の回に、声を付ける（GitHub Actions が台本の push のたびに動かす）。

対象：各チャンネルの episodes/ のうち、直近 --days 日（既定 3 日）の台本で、
      音声ファイルがない、または字幕のタイミング（lines_timed）がないもの。
1 つ失敗しても、ほかは続ける。失敗があれば終了コード 1。

usage: python3 tools/voice_pending.py [--days 3]
"""
import datetime, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R
import voice


def main():
    days = int(R.arg(sys.argv[1:], "--days", "3"))
    since = R.today_jst() - datetime.timedelta(days=days)
    bad = 0
    for cid in R.channels():
        d = os.path.join(R.chan_dir(cid), "episodes")
        st = R.station(cid); adir = os.path.join(R.chan_dir(cid), (st.get("audio") or {}).get("dir", "audio"))
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not f.endswith("-ja.json"): continue
            date = f[:10]
            if date < str(since): continue
            ep = R.load_json(os.path.join(d, f), {})
            if ep.get("lines_timed") and os.path.exists(os.path.join(adir, f"{date}-ja.mp3")): continue
            try:
                voice.make(cid, date, force=True)
            except BaseException:
                traceback.print_exc(); bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
