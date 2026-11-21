# 毎朝の台本づくり（Claude の定期タスク用の手順）

毎朝 5 時台に GitHub Actions（`collect.yml`）が各チャンネルの候補記事を集め、`inbox` ブランチの `inbox/<日付>/<ID>.json` に置きます。
この手順で台本を書いて `main` に push すると、GitHub Actions（`daily.yml`）が声を作って GitHub Pages に公開します。

## 手順

1. リポジトリを取得し、今日（日本時間）の inbox を取る
   ```bash
   git clone https://github.com/razanohito/asa-radio && cd asa-radio
   git fetch origin inbox && git restore --source=origin/inbox --worktree -- inbox
   D=$(TZ=Asia/Tokyo date +%F)
   ls inbox/$D/
   ```
   `inbox/$D/` がなければ（収集が動いていない）、何も書かずに終わり、その旨を報告する。
2. チャンネルごとに（`channels.json` の順。inbox にあるチャンネルだけ）:
   1. `inbox/$D/<ID>.json` を読む。`news` に番組のテーマ・キャスター・口調・追加の決まり、`candidates` に記事（題・URL・本文）がある
   2. テーマに合う記事を `news.count` 本まで選ぶ（決まりは下）。合う記事が `news.min` 本に満たなければ、そのチャンネルは今日はお休み（台本を作らない）
   3. 下書きを `/tmp/<ID>.json` に書く（形は下）
   4. `python3 tools/save_script.py --channel <ID> --draft /tmp/<ID>.json` で確かめて保存する。「直すべき点」が出たら直して、もう一度
3. 保存した台本を commit して push する
   ```bash
   git add channels/*/episodes
   git commit -m "台本 $D"
   git push origin HEAD:main
   ```
   push すると、声と公開は GitHub Actions が自動で行う。
4. チャンネルごとの結果（放送した本数と題、お休みの理由）を短く報告する

`inbox/` は main に commit しない（`.gitignore` 済み）。上の `git restore --worktree` で取れば、コミット待ちにならない（`git checkout origin/inbox -- inbox` だとコミット待ちに入ってしまう）。

## 記事を選ぶ決まり

- 番組のテーマ（`news.topic`）に合う、きのう〜けさの新しい発表・出来事。同じ出来事は 1 本だけ
- 宣伝だけの記事、うわさ、真偽のはっきりしない投稿、セール情報は選ばない
- `news.pick_rules` があれば従う

## 台本の決まり

- 事実は、その記事の本文（`candidates[].body`）に書いてあることだけ（本文が題と無関係な定型文やリンクだけのときは、`candidates[].summary` を本文の代わりにしてよい。そのときは要約にあることだけを話す）。数字・名前・日付は本文どおり。推測や本文にない情報は入れない。感想は一言だけ、断定しない
- 記事が英語でも、台本は日本語
- 話す文は `{"say": 読み上げ用, "show": 字幕用}`
  - `say` は音声合成用。英字の名前・略語はカタカナにし、**アルファベットを一文字も残さない**（OpenAI→オープンエーアイ、GPT→ジーピーティー、Google→グーグル）。記号も言葉にする（%→パーセント）。数字はそのままでよいが、製品の型番はふつうの読み方をカタカナで（RTX 5090→アールティーエックス ゴーマルキューマル）
  - `show` はふつうの表記で、短く（30 字以内目安）
- 1 文は短く（`say` で 60 字以内）。聞いてわかる言い方。口調は `news.tone`、キャスターは `news.caster_name`（`news.persona`）
- `news.write_rules` があれば従う
- 全体で 2 分前後

## 下書きの形

```json
{
 "title": "今日の回の題（25字以内、いちばん大きなニュースから）",
 "opening": [
  {"say": "<番組名>です。<十一月八日日曜日>、おはようございます。", "show": "<番組名>です。<11月8日日曜日>、おはようございます。"},
  {"say": "今日は<三>本のニュースをお届けします。", "show": "今日は<3>本のニュースをお届けします。"}
 ],
 "news": [
  {
   "label": "見出し（14字以内）",
   "points": ["要点（18字以内）", "…", "…"],
   "details": ["points と同じ数の、くわしい説明（各60字以内、本文の範囲で）", "…", "…"],
   "lines": [{"say": "…", "show": "…"}, {"say": "…", "show": "…"}],
   "url": "inbox の candidates[].url をそのまま"
  }
 ],
 "closing": [
  {"say": "今日のニュースをひとことでまとめる", "show": "…"},
  {"say": "<news.farewell があればそれ、なければ「それでは今日も、いってらっしゃい。」><番組名>でした。", "show": "…"}
 ],
 "highlight": 0
}
```

- 番組名は inbox の `name`。日付は日本時間の今日
- 2 本目以降の `lines` の 1 文目は「続いては」「次は」など、つなぎの言葉で始める
- `lines` は 2〜3 文、`points` は 3 つ
