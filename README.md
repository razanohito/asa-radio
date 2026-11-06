# あさAIラジオ

**生成AI・AIの、きのうの気になるニュースを、毎朝 2 分で。**
キャスターのアサヒが、毎朝 6 時台に読み上げる HTML の番組です。

- 毎朝 GitHub Actions が自動で放送します：ニュースを集める → Claude が台本を書く → VOICEVOX で声を作る → GitHub Pages に公開
- 動画ではなく HTML の番組です。再生位置に合わせて、スライド・字幕・キャラ・リンクカードが動きます
- ニュースの画像は、記事のサイトが共有用に公開している画像（OGP）をそのまま表示し、記事へのリンクを添えます（画像は保存しません）
- 台本はずっと残り、音声は直近 30 日分だけを公開します

このリポジトリは [myradio](https://github.com/monoradio102/myradio) のテンプレートから作りました。

## 毎朝の自動放送のしくみ

`.github/workflows/daily.yml`（日本時間 6:17 ごろに起動）

| 順番 | やること | 道具 |
|---|---|---|
| 1 | `station.json` の `news.feeds` の RSS から、直近 36 時間の記事を集める | `tools/radiolib.py` |
| 2 | Claude API が放送する記事を選ぶ | `tools/make_script.py` |
| 3 | 選んだ記事のページを読み、OGP と本文を取る（読めない記事は外す） | `tools/make_script.py` |
| 4 | Claude API が、本文だけを根拠に台本（`episodes/<日付>-ja.json`）を書く。形を確かめ、だめなら直させる | `tools/make_script.py` |
| 5 | VOICEVOX で 1 文ずつ声を作り、つないで mp3 にし、字幕のタイミングを台本に書く | `tools/voice.py` |
| 6 | 台本を main に記録し、`gh-pages` に「main＋直近 30 日の声」を公開する | `tools/publish.sh` |

## 初めにやる設定（1 回だけ）

1. **Claude API のキー**：Settings → Secrets and variables → Actions → New repository secret で、名前 `ANTHROPIC_API_KEY` にキーを登録（キーは https://console.anthropic.com で作れます。1 回分の費用は数円〜十数円ほど）
2. **GitHub Pages**：Settings → Pages → Build and deployment を「Deploy from a branch」、ブランチ `gh-pages` / `(root)` にする
3. **Actions の書き込み権限**：Settings → Actions → General → Workflow permissions を「Read and write permissions」にする
4. **試しに放送**：Actions → 「毎朝の放送」→ Run workflow

モデルを変えたいときは、Settings → Secrets and variables → Actions → Variables に `CLAUDE_MODEL` を作るか、`station.json` の `news.model` を書き換えます。

## 変えられるところ（station.json）

| 欄 | 中身 |
|---|---|
| `name`、`tagline`、`description` | 局の名前・副題・説明 |
| `news.feeds` | ニュースを集める RSS / Atom |
| `news.count` | 1 回のニュースの本数（既定 5） |
| `voice.speaker` | VOICEVOX の話者 ID（既定 8：春日部つむぎ）。変えたら `credits` と `caster` も書き換える |
| `voice.speed` | 話す速さ（既定 1.1） |
| `voice.pause_line`、`voice.pause_part` | 文と文、パートとパートの間（秒） |

## キャスターの差し替え

いまの「アサヒ」は、`tools/make_character.py` がプログラムで描いた仮のキャラです。本番の絵に替えるときは：

1. `character/base.png`（口を閉じて正面、背景透明、896×768）を置く
2. 口（半開き・開き・笑顔）と目（閉じ・半目）の差分を、変わった範囲だけ切り出して置く
3. `character/character.json` の各画像の `x`、`y`（base の上に重ねる位置）を書き換える

くわしい形は [docs/formats.md](docs/formats.md) の「キャラパック」。

## 手で放送するとき

```bash
# VOICEVOX エンジンを起動しておく（http://127.0.0.1:50021）
ANTHROPIC_API_KEY=... python3 tools/make_script.py   # 台本（今日の分）
python3 tools/voice.py                                # 声
bash tools/publish.sh                                 # 公開
```

台本を手で書いた場合は、`episodes/<日付>-ja.json` を置いて `tools/voice.py --date <日付>` から。

## 中身

```
station.json                 局の設定（名前・ニュースの集め先・声）
index.html                   プレーヤー
episodes.json                回の一覧
episodes/<日付>-ja.json       台本とタイミング
audio/<日付>-ja.mp3           声（main にはコミットしない）
character/                   キャスター（アサヒ）
tools/make_script.py         ニュース集め・台本づくり（Claude API）
tools/voice.py               声づくり（VOICEVOX）とタイミング
tools/radiolib.py            共通の部品（フィード・OGP・台本の確認）
tools/make_character.py      仮キャラの差分画像を作る
tools/publish.sh             GitHub Pages への公開
tools/share.py               SNS 用の共有カード
.github/workflows/daily.yml  毎朝の自動放送
```

## ライセンス・クレジット

- プログラム（`index.html`、`tools/`）：MIT License（myradio のものを含みます）
- 声：VOICEVOX:春日部つむぎ（[利用規約](https://tsumugi-official.studio.site/rule)に従って利用）
- ニュースの画像・題：各記事のサイトのもの（OGP を表示しているだけで、保存・再配布はしていません）
- 天気：Open-Meteo（CC BY 4.0）
