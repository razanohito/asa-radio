"""全チャンネル（または指定したチャンネル）の、その日の放送を作る：台本 → 声。

1 つのチャンネルが失敗しても、ほかのチャンネルは続けます。最後に結果の一覧を出し、
失敗したチャンネルがあれば終了コード 1（ニュースが足りずにお休みしたのは失敗にしない）。

usage: python3 tools/broadcast.py [--channels ai,tech] [--date YYYY-MM-DD] [--force]
"""
import datetime, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R
import make_script, voice


def main():
    args = sys.argv[1:]
    ids = [c for c in R.arg(args, "--channels", "").split(",") if c] or R.channels()
    date = datetime.date.fromisoformat(R.arg(args, "--date")) if "--date" in args else R.today_jst()
    force = "--force" in args
    results = []
    for cid in ids:
        print(f"\n===== {cid} =====")
        try:
            if R.station(cid).get("paused"):
                results.append((cid, "停止中")); continue
            make_script.make(cid, date, force)
            voice.make(cid, str(date), force)
            results.append((cid, "放送"))
        except make_script.Skip as e:
            results.append((cid, f"お休み（{e}）"))
        except BaseException as e:
            traceback.print_exc()
            results.append((cid, f"失敗：{e}"))
    print("\n===== 結果 =====")
    for cid, r in results: print(f"{cid}: {r}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### {date} の放送\n\n| チャンネル | 結果 |\n|---|---|\n" + "".join(f"| {c} | {r} |\n" for c, r in results))
    sys.exit(1 if any(r.startswith("失敗") for _, r in results) else 0)


if __name__ == "__main__":
    main()
