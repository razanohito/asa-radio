"""その日の台本（episodes/<日付>-ja.json）を作る。

1. station.json の news.feeds から、直近の AI ニュースを集める
2. Claude API に、放送する記事を選んでもらう
3. 選んだ記事のページを読み、リンクカード（OGP）と本文を取る
4. Claude API に、本文だけを根拠に台本を書いてもらう（形を確かめ、だめなら直してもらう）

usage: ANTHROPIC_API_KEY=... python3 tools/make_script.py [--date YYYY-MM-DD] [--force]
  --date   放送日（既定：今日・日本時間）
  --force  その日の台本がもうあっても作り直す
  --feeds  フィードの URL（カンマ区切り。既定：station.json の news.feeds）
環境変数：ANTHROPIC_API_KEY（必須）、CLAUDE_MODEL（station.json の news.model より優先）、ANTHROPIC_BASE_URL（テスト用）
"""
import datetime, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import radiolib as R

API = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"


def claude(system, user, max_tokens=8000):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("ANTHROPIC_API_KEY がありません（GitHub の Settings → Secrets に登録してください）")
    model = os.environ.get("CLAUDE_MODEL") or (R.station().get("news") or {}).get("model") or "claude-sonnet-5-5"
    body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            return "".join(c.get("text", "") for c in d.get("content", []) if c.get("type") == "text")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 500, 502, 503, 529) and attempt < 3:
                print(f"  API {e.code}、{10 * (attempt + 1)} 秒待って再試行"); time.sleep(10 * (attempt + 1)); continue
            sys.exit(f"Claude API エラー {e.code}: {msg}")
        except Exception as e:
            if attempt < 3: print(f"  API 接続失敗（{e}）、再試行"); time.sleep(10); continue
            raise


def json_from(text):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m: text = m.group(1)
    a, b = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1), max(text.rfind("}"), text.rfind("]"))
    if a < 0 or b < a: raise ValueError("JSON が見つからない")
    return json.loads(text[a:b + 1])


PICK_SYSTEM = """あなたは、生成AI・AIの朝のニュース番組の編集者です。候補の記事一覧から、放送する記事を選びます。
選ぶ基準：
- 生成AI・AIの話題であること（AIと無関係な記事は選ばない）
- きのう〜けさの新しい発表・出来事であること。同じ出来事の記事は1つだけ
- 大手の新モデル・新サービス、日本の企業や行政の動き、研究の成果、身近な使い道など、話題がかたよらないように
- 宣伝だけの記事、うわさ、セール情報、レビュー記事は避ける
答えは JSON の配列だけ：選んだ候補の番号を、放送する順に。予備として指定本数より3本多く選ぶ。"""

WRITE_SYSTEM = """あなたは朝のラジオ「{name}」の台本作家です。キャスターは明るく落ち着いた女性「アサヒ」。番組は{date_words}放送、全体で2分前後。
渡された記事の本文に書いてあることだけを使い、台本を JSON で書きます。

決まり：
- 事実は本文に書いてあることだけ。数字・名前・日付は本文どおり。推測や本文にない情報は入れない。感想は一言だけ、断定しない
- 話す文は {{"say": 読み上げ用, "show": 字幕用}}。say は音声合成用：英字の名前・略語はカタカナ（OpenAI→オープンエーアイ、GPT→ジーピーティー、Google→グーグル）にし、say にはアルファベットを一文字も残さない。記号（%、/、&など）も言葉にする（%→パーセント）。数字はそのままでよい。show はふつうの表記で、短く（30字以内目安）
- 1文は短く（say で60字以内）。聞いてわかる言い方にする
- opening：2文。1文目は「{name}です。{date_words}、おはようございます。」、2文目で今日の本数
- news：各ニュースに label（見出し、14字以内）、points（要点3つ、各18字以内）、details（points と同じ数の、くわしい説明。各60字以内、本文の範囲で）、lines（話す文 2〜3 文）、url（渡した記事の URL をそのまま）
- 2本目以降の lines の1文目は「続いては」「次は」など、つなぎの言葉で始める
- closing：2文。今日のニュースをひとことでまとめ、最後は「それでは今日も、いってらっしゃい。{name}でした。」
- title：今日の回の題（25字以内、いちばん大きなニュースから）
- highlight：締めで取り上げるニュースの番号（0から）
出力は JSON だけ：{{"title", "opening", "news", "closing", "highlight"}}"""


def main():
    args = sys.argv[1:]
    date = datetime.date.fromisoformat(args[args.index("--date") + 1]) if "--date" in args else R.today_jst()
    out = os.path.join(R.ROOT, "episodes", f"{date}-ja.json")
    if os.path.exists(out) and "--force" not in args:
        print(f"{out} はもうあります（作り直すなら --force）"); return
    st = R.station(); cfg = st.get("news") or {}
    count = int(cfg.get("count", 5))

    print("1) ニュースを集める")
    feeds = args[args.index("--feeds") + 1].split(",") if "--feeds" in args else cfg.get("feeds", [])
    cands = R.collect(feeds, hours=int(cfg.get("hours", 36)))
    if len(cands) < 3: sys.exit(f"候補の記事が少なすぎます（{len(cands)} 本）。フィードを確かめてください")
    cands = cands[:120]
    print(f"   候補 {len(cands)} 本")

    print("2) 放送する記事を選ぶ")
    listing = "\n".join(f"[{i}] {c['title']}（{c['source']}）{c['summary'][:120]}" for i, c in enumerate(cands))
    pick = json_from(claude(PICK_SYSTEM, f"指定本数：{count} 本（予備込みで {count + 3} 本選ぶ）\n\n候補：\n{listing}", 1000))
    pick = [i for i in pick if isinstance(i, int) and 0 <= i < len(cands)]

    print("3) 記事のページを読む")
    articles = []
    for i in pick:
        link, body = R.page_info(cands[i]["url"])
        if "status" in link or len(body) < 200:
            print(f"   × {cands[i]['title'][:40]}（{link.get('status', '本文なし')}）"); continue
        articles.append({"url": cands[i]["url"], "title": cands[i]["title"], "source": cands[i]["source"], "link": link, "body": body})
        print(f"   ○ {cands[i]['title'][:40]}")
        if len(articles) >= count: break
    if len(articles) < 2: sys.exit("読めた記事が 2 本未満です")

    print("4) 台本を書く")
    name = st.get("name", "ラジオ")
    system = WRITE_SYSTEM.format(name=name, date_words=R.date_words(date))
    user = f"今日は {len(articles)} 本のニュースです。記事：\n\n" + "\n\n".join(
        f"### 記事{k + 1}\nURL: {a['url']}\n題: {a['title']}\nサイト: {a['link']['site']}\n本文:\n{a['body'][:3500]}" for k, a in enumerate(articles))
    urls = {a["url"] for a in articles}
    ep, errs = None, []
    for attempt in range(3):
        msg = user if not errs else user + "\n\n前回の台本には次の問題がありました。直して、台本全体を JSON で出し直してください：\n- " + "\n- ".join(errs[:20])
        try:
            ep = json_from(claude(system, msg))
            errs = R.check_script(ep, urls) if isinstance(ep, dict) else ["JSON がオブジェクトではない"]
        except (ValueError, json.JSONDecodeError) as e:
            errs = [f"JSON として読めない：{e}"]
        if not errs: break
        print(f"   直しが要る（{len(errs)} 件）：{errs[:3]}")
    if errs: sys.exit("台本が決まりを満たしませんでした：\n" + "\n".join(errs))

    by_url = {a["url"]: a for a in articles}
    for n in ep["news"]:
        n["link"] = by_url[n["url"]]["link"]
    ep = {"format": "monoradio/news-1", "date": str(date), "lang": "ja", "title": ep["title"], "opening": ep["opening"],
          "news": ep["news"], "closing": ep["closing"], **({"highlight": ep["highlight"]} if "highlight" in ep else {})}
    R.save_json(out, ep)
    print(f"台本：{out}（{len(ep['news'])} 本）「{ep['title']}」")


if __name__ == "__main__":
    main()
