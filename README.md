# あさラジオ

**キャラクターが毎朝ニュースを読む、3 つのチャンネル。**

| チャンネル | 内容 | キャスター | 声 |
|---|---|---|---|
| あさAIラジオ（`channels/ai`） | 生成AI・AIのニュース。毎朝 5 本 | アサヒ | VOICEVOX:春日部つむぎ |
| あさテックラジオ（`channels/tech`） | スマホ・PC・ネット・セキュリティなどのテックニュース。毎朝 5 本 | ミライ | VOICEVOX:冥鳴ひまり |
| サマナ朝通信（`channels/summoners`） | 『サマナーズウォー』の非公式ニュース。新しい話題がある日だけ、最大 3 本 | ルナ | VOICEVOX:四国めたん |

- 毎朝 GitHub Actions が全チャンネルを自動で放送します：ニュースを集める → Claude が台本を書く → VOICEVOX で声を作る → GitHub Pages に公開
- トップページ（`index.html`）がチャンネルの一覧で、それぞれの番組ページ（`channels/<ID>/`）へ進めます
- 動画ではなく HTML の番組です。再生位置に合わせて、スライド・字幕・キャラ・リンクカードが動きます
- ニュースの画像は、記事のサイトが共有用に公開している画像（OGP）をそのまま表示し、記事へのリンクを添えます（画像は保存しません）
- 台本はずっと残り、音声は直近 30 日分だけを公開します。一度放送した記事は、同じチャンネルで二度は取り上げません

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
| 6 | 全チャンネルの台本を main に記録し、`gh-pages` に「main＋直近 30 日の声」を公開する | `tools/publish.sh` |

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
| `voice.speaker` | VOICEVOX の話者 ID。変えたら `credits` と `caster` も書き換える |
| `voice.speed`、`pause_line`、`pause_part` | 話す速さ、文と文・パートとパートの間（秒） |

## チャンネルを増やすとき

1. `channels/<新しいID>/` を作り、ほかのチャンネルの `station.json` をまねて書く（`episodes.json` は `[]`、`logo.svg` も置く）
2. キャラ：`tools/make_character.py` の `THEMES` に色と小物を足して `python3 tools/make_character.py <新しいID>`（または自分の絵を置く）
3. `channels.json` の `channels` に `{"id": "<新しいID>"}` を足す

## キャスターの差し替え

いまの 3 人は、`tools/make_character.py` がプログラムで描いた仮のキャラです。本番の絵に替えるときは、そのチャンネルの `character/` に：

1. `base.png`（口を閉じて正面、背景透明、896×768）を置く
2. 口（半開き・開き・笑顔）と目（閉じ・半目）の差分を、変わった範囲だけ切り出して置く
3. `character.json` の各画像の `x`、`y`（base の上に重ねる位置）を書き換える

くわしい形は [docs/formats.md](docs/formats.md) の「キャラパック」。

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
- 声：VOICEVOX:春日部つむぎ、VOICEVOX:冥鳴ひまり、VOICEVOX:四国めたん（それぞれの利用規約に従って利用）
- サマナ朝通信は非公式のファン番組で、Com2uS とは関係ありません。『サマナーズウォー』は Com2uS の商標です
- ニュースの画像・題：各記事のサイトのもの（OGP を表示しているだけで、保存・再配布はしていません）
- 天気：Open-Meteo（CC BY 4.0）
