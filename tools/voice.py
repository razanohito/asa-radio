"""台本から声を作る（VOICEVOX）。文ごとの開始・終了の秒（lines_timed）とパートの区切り（segments）も台本に書く。

usage: python3 tools/voice.py [--date YYYY-MM-DD] [--engine http://127.0.0.1:50021] [--force]
  台本 episodes/<日付>-ja.json → 声 audio/<日付>-ja.mp3、episodes.json も更新
  --force  声がもうあっても作り直す
VOICEVOX エンジンを動かしておくこと（GitHub Actions では .github/workflows/daily.yml が起動する）。
話者・速さ・間は station.json の voice（speaker, speed, pause_line, pause_part）。
"""
import datetime, io, json, os, subprocess, sys, time, urllib.parse, urllib.request, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R

LEAD = 0.6    # 番組の頭の無音（秒）
TAIL = 1.0    # 終わりの無音


def vv(engine, path, data=None, params=None, raw=False):
    url = engine.rstrip("/") + path + ("?" + urllib.parse.urlencode(params) if params else "")
    body = json.dumps(data).encode() if data is not None else b""
    req = urllib.request.Request(url, data=body, method="POST", headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = r.read()
    return out if raw else json.loads(out)


def synth(engine, text, cfg):
    q = vv(engine, "/audio_query", params={"text": text, "speaker": cfg["speaker"]})
    q["speedScale"] = cfg.get("speed", 1.0)
    q["pitchScale"] = cfg.get("pitch", 0.0)
    q["intonationScale"] = cfg.get("intonation", 1.15)
    q["prePhonemeLength"], q["postPhonemeLength"] = 0.0, 0.05
    q["outputSamplingRate"], q["outputStereo"] = 24000, False
    w = vv(engine, "/synthesis", data=q, params={"speaker": cfg["speaker"]}, raw=True)
    with wave.open(io.BytesIO(w)) as f:
        return f.readframes(f.getnframes()), f.getframerate(), f.getsampwidth()


def main():
    args = sys.argv[1:]
    date = args[args.index("--date") + 1] if "--date" in args else str(R.today_jst())
    engine = args[args.index("--engine") + 1] if "--engine" in args else os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
    st = R.station(); cfg = {"speaker": 8, "speed": 1.1, "pause_line": 0.25, "pause_part": 0.8, **(st.get("voice") or {})}
    ep_path = os.path.join(R.ROOT, "episodes", f"{date}-ja.json")
    ep = R.load_json(ep_path)
    if not ep: sys.exit(f"台本がありません：{ep_path}")
    adir = os.path.join(R.ROOT, (st.get("audio") or {}).get("dir", "audio"))
    mp3 = os.path.join(adir, f"{date}-ja.mp3")
    if os.path.exists(mp3) and ep.get("lines_timed") and "--force" not in args:
        print(f"{mp3} はもうあります（作り直すなら --force）"); return
    errs = R.check_script(ep)
    if errs: sys.exit("台本の形がおかしい：\n" + "\n".join(errs))

    for i in range(60):   # エンジンの起動待ち
        try: urllib.request.urlopen(engine.rstrip("/") + "/version", timeout=5).read(); break
        except Exception: time.sleep(3)
    else: sys.exit(f"VOICEVOX エンジンにつながりません：{engine}")

    parts = [("opening", None, ep["opening"])] + [("news", j, n["lines"]) for j, n in enumerate(ep["news"])] + [("closing", None, ep["closing"])]
    pcm, rate, width = bytearray(), 24000, 2
    silence = lambda sec: b"\0" * (int(sec * rate) * width)
    pcm += silence(LEAD)
    t = lambda: len(pcm) / (rate * width)
    timed, segs = [], []
    for p, (kind, idx, lines) in enumerate(parts):
        if p: pcm += silence(cfg["pause_part"])
        seg_start = t()
        for k, line in enumerate(lines):
            if k: pcm += silence(cfg["pause_line"])
            frames, rate, width = synth(engine, line["say"], cfg)
            start = t(); pcm += frames
            timed.append({"start": round(start, 3), "end": round(t(), 3), "show": line["show"], "part": p})
        segs.append({"kind": kind, "index": idx, "start": round(seg_start, 3), "end": None})
        print(f"  {kind}{'' if idx is None else idx}: {len(lines)} 文")
    pcm += silence(TAIL)
    total = round(t(), 2)
    for a, b in zip(segs, segs[1:]): a["end"] = b["start"]
    segs[-1]["end"] = total

    os.makedirs(adir, exist_ok=True)
    wav = mp3[:-4] + ".wav"
    with wave.open(wav, "wb") as f:
        f.setnchannels(1); f.setsampwidth(width); f.setframerate(rate); f.writeframes(bytes(pcm))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k", mp3], check=True)
    os.remove(wav)

    ep.update({"seconds": total, "lines_timed": timed, "segments": segs,
               "made_at": datetime.datetime.now(R.JST).replace(microsecond=0, tzinfo=None).isoformat()})
    R.save_json(ep_path, ep)

    lst_path = os.path.join(R.ROOT, st.get("episodes", "episodes.json"))
    lst = [e for e in (R.load_json(lst_path, []) or []) if e.get("date") != date]
    lst.append({"date": date, "ja": {"title": ep["title"], "seconds": total}})
    lst.sort(key=lambda e: e["date"], reverse=True)
    with open(lst_path, "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False); f.write("\n")
    print(f"声：{mp3}（{total} 秒、{os.path.getsize(mp3) // 1024} KB）")


if __name__ == "__main__":
    main()
