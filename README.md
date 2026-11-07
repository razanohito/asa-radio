# あさラジオ

**キャラクターが毎朝ニュースを読む、4 つのチャンネル。**

| チャンネル | 内容 | キャスター | 声 |
|---|---|---|---|
| あさAIラジオ（`channels/ai`） | 生成AI・AIのニュース。毎朝 5 本 | こうはい | VOICEVOX:春日部つむぎ |
| あさテックラジオ（`channels/tech`） | スマホ・PC・ネット・セキュリティなどのテックニュース。毎朝 5 本 | ミライ | VOICEVOX:冥鳴ひまり |
| サマナ朝通信（`channels/summoners`） | 『サマナーズウォー』の非公式ニュース。新しい話題がある日だけ、最大 3 本 | せんぱい | VOICEVOX:四国めたん |
| あさワークスペース通信（`channels/workspace`） | Google Workspace の更新情報（非公式）。毎朝最大 4 本 | シオリ | VOICEVOX:九州そら |

- 毎朝 GitHub Actions が全チャンネルを自動で放送します：ニュースを集める → Claude が台本を書く → VOICEVOX で声を作る → GitHub Pages に公開
- トップページ（`index.html`）がチャンネルの一覧で、それぞれの番組ページ（`channels/<ID>/`）へ進めます
- 動画ではなく HTML の番組です。再生位置に合わせて、スライド・字幕・キャラ・リンクカードが動きます
- ニュースの画像は、記事のサイトが共有用に公開している画像（OGP）をそのまま表示し、記事へのリンクを添えます（画像は保存しません）
- 台本はずっと残ります。音声はサマナ朝通信は全部、ほかのチャンネルは直近 90 日分を公開します（過去の回はプレーヤーの一覧から聴けます）。一度放送した記事は、同じチャンネルで二度は取り上げません

このリポジトリは [myradio](https://github.com/monoradio102/myradio) のテンプレートを、複数チャンネルに広げて作りました。

## 毎朝の自動放送のしくみ

`.github/workflows/daily.yml`（日本時間 6:17 ごろに起動）が、`channels.json` の順に、チャンネルごとに次を行います。

| 順番 | やること | 道具 |
|---|---|---|
| 1 | `station.json` の `news.feeds` の RSS から、直近 `news.hours` 時間の記事を集める（放送済みの記事は外す） | `tools/radiolib.py` |
| 2 | Claude API が、チャンネルのテーマに合う記事を選ぶ | `tools/make_script.py` |
| 3 | 選んだ記事のページを読み、OGP と本文を取る（読めない記事は外す） | `tools/make_script.py` |
| 4 | Claude API が、本文だけを根拠に台本（`episodes/<日付>-ja.json`）を書く。形を確かめ、だめなら直させる | `tools/make_script.py` |
| 5 | VOICEVOX で 1 文ずつ声を作り、つないで mp3 にし、字幕のタイミングを台本に書く | `tools/voice.py` |
| 6 | 全チャンネルの台本を main に記録し、`gh-pages` に「main＋各チャンネルの残す日数分の声」を公開する | `tools/publish.sh` |

1 つのチャンネルが失敗しても、ほかのチャンネルは放送して公開します（失敗した回は Actions の実行が赤くなり、GitHub からメールが届きます）。
ニュースが足りないチャンネルはその日お休みで、失敗にはなりません。

## 初めにやる設定（1 回だけ）

1. **Claude API のキー**：Settings → Secrets and variables → Actions → New repository secret で、名前 `ANTHROPIC_API_KEY` にキーを登録（https://console.anthropic.com で作れます）
2. **GitHub Pages**：Settings → Pages → Build and deployment を「Deploy from a branch」、ブランチ `gh-pages` / `(root)` にする
3. **Actions の書き込み権限**：Settings → Actions → General → Workflow permissions を「Read and write permissions」にする
4. **試しに放送**：Actions → 「毎朝の放送」→ Run workflow（チャンネルを絞るなら `ai,tech` のように入力）

モデルを変えたいときは、Settings → Secrets and variables → Actions → Variables に `CLAUDE_MODEL` を作るか、各チャンネルの `station.json` の `news.model` を書き換えます。

## チャンネルの設定（channels/<ID>/station.json）

| 欄 | 中身 |
|---|---|
| `name`、`tagline`、`description` | チャンネルの名前・副題・説明 |
| `theme.accent` | チャンネルの色（プレーヤー・トップページ・共有カードの強調色） |
| `paused` | `true` にすると、そのチャンネルの放送を止める |
| `news.topic` | 番組のテーマ（記事選びと台本の基準） |
| `news.feeds` | ニュースを集める RSS / Atom。`{"url": …, "keywords": […]}` と書くと、そのフィードは題か要約にキーワードを含む記事だけ |
| `news.count`、`news.min` | 1 回のニュースの本数と、放送する最低本数（足りなければお休み） |
| `news.hours` | 何時間前までの記事を集めるか（サマナは 168 時間＝7 日） |
| `news.caster_name`、`persona`、`tone`、`farewell` | キャスターの名前・人物像・口調・締めのあいさつ |
| `news.pick_rules`、`news.write_rules` | 記事選び・台本づくりの追加の決まり |
| `audio.keep_days` | 音声を公開しておく日数（`0` で全部残す）。それより古い回は台本だけ読める。音声は `tools/voice.py --channel <ID> --date <日付> --force` でいつでも作り直せる |
| `voice.speaker` | VOICEVOX の話者 ID。変えたら `credits` と `caster` も書き換える |
| `voice.speed`、`pause_line`、`pause_part` | 話す速さ、文と文・パートとパートの間（秒） |

## チャンネルを増やすとき

1. `channels/<新しいID>/` を作り、ほかのチャンネルの `station.json` をまねて書く（`episodes.json` は `[]`、`logo.svg` も置く）
2. キャラ：立ち絵があれば `tools/import_character.py <新しいID> …`。なければ `tools/make_character.py` の `THEMES` に足して仮キャラを作る
3. `channels.json` の `channels` に `{"id": "<新しいID>"}` を足す

## キャスター

こうはい・せんぱいは、ゆっくり解説シリーズ（yukkuri-video-maker）のキャラクターです。テックのミライとワークスペースのシオリは ChatGPT で作りました。
手持ちの立ち絵（口閉じ・口開き・笑顔の PNG）を取り込むときは `tools/import_character.py` を使います。

```bash
python3 tools/import_character.py ai --closed normal_closed.png --open normal_open.png --smile smile_closed.png --bg "#161a26" --name こうはい
# AI で描いた差分のように顔全体が少しずつ違う絵は、口の範囲を指定するときれいに口だけ動きます
python3 tools/import_character.py ai ... --mouth-box 432,422,522,474
```

絵は 896×768 の枠に下ぞろえで収め、口や目の変わった範囲だけを小さな画像に切り出して `character.json` を書きます。
`tools/make_character.py` は、立ち絵がないチャンネル用の仮キャラ（プログラムで描画）を作る道具です。

## 手で放送するとき

```bash
# VOICEVOX エンジンを起動しておく（http://127.0.0.1:50021）
ANTHROPIC_API_KEY=... python3 tools/broadcast.py                 # 全チャンネルの台本と声（今日の分）
ANTHROPIC_API_KEY=... python3 tools/make_script.py --channel ai  # 1 チャンネルの台本だけ
python3 tools/voice.py --channel ai                              # 1 チャンネルの声だけ
bash tools/publish.sh                                            # 公開
python3 tools/site.py local                                      # 手元で見るとき（各チャンネルにプレーヤーを置く）
```

## 中身

```
index.html                       トップページ（チャンネル一覧）
player.html                      番組のプレーヤー（公開時に各チャンネルの index.html になる）
channels.json                    サイトの名前・公開先と、チャンネルの並び
channels/<ID>/station.json       チャンネルの設定（名前・色・ニュースの集め先・キャスター・声）
channels/<ID>/episodes.json      回の一覧
channels/<ID>/episodes/          台本とタイミング
channels/<ID>/audio/             声（main にはコミットしない）
channels/<ID>/character/         キャスター
tools/broadcast.py               全チャンネルの放送（台本→声）
tools/make_script.py             ニュース集め・台本づくり（Claude API）
tools/voice.py                   声づくり（VOICEVOX）とタイミング
tools/radiolib.py                共通の部品（チャンネル・フィード・OGP・台本の確認）
tools/site.py                    公開・手元確認の下ごしらえ
tools/make_character.py          仮キャラの差分画像を作る
tools/publish.sh                 GitHub Pages への公開
tools/share.py                   SNS 用の共有カード
.github/workflows/daily.yml      毎朝の自動放送
```

## ライセンス・クレジット

- プログラム（`index.html`、`player.html`、`tools/`）：MIT License（myradio のものを含みます）
- 声：VOICEVOX:春日部つむぎ、VOICEVOX:冥鳴ひまり、VOICEVOX:四国めたん、VOICEVOX:九州そら（それぞれの利用規約に従って利用）
- サマナ朝通信は非公式のファン番組で、Com2uS とは関係ありません。『サマナーズウォー』は Com2uS の商標です
- あさワークスペース通信は非公式の番組で、Google とは関係ありません。Google Workspace は Google LLC の商標です
- ニュースの画像・題：各記事のサイトのもの（OGP を表示しているだけで、保存・再配布はしていません）
- 天気：Open-Meteo（CC BY 4.0）
