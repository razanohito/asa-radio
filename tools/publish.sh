#!/bin/bash
# 局（全チャンネル）を GitHub Pages に公開する：gh-pages ブランチを「main の中身＋各チャンネルの直近の音声」のコミット 1 つで上書きする。
# 音声は git の履歴に入らない（古い音声は履歴ごと消える）。直近の日数は各チャンネルの station.json の audio.keep_days（既定 30 日、0 か null で全部残す）。
# usage: tools/publish.sh   （リポジトリの中で。origin に push できること）
#   PUBLISH_REMOTE  送り先（既定：origin。GitHub Actions ではトークン付きの URL を渡す）
#   SHARE_FONT      共有カードに使う日本語フォント（tools/share.py）。Pillow がなければカードは作らない
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
REMOTE=${PUBLISH_REMOTE:-$(git remote get-url origin)}
NAME=$(git config user.name || echo myradio); EMAIL=$(git config user.email || echo myradio@users.noreply.github.com)
PY=${SHARE_PYTHON:-python3}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git archive HEAD | tar -x -C "$TMP"              # main にコミットされているもの

# 各チャンネル：プレーヤーを置き、公開先を station.json に書き、直近の音声をコピーし、共有カードを作る
python3 tools/site.py prepare "$TMP"
total=0
for cdir in channels/*/; do
  cid=$(basename "$cdir")
  [ -f "$cdir/station.json" ] || continue
  read -r DIR KEEP < <(python3 -c "import json; a = json.load(open('$cdir/station.json')).get('audio', {}); k = a.get('keep_days', 30); print(a.get('dir', 'audio'), 0 if not k else int(k))")
  if [ "$KEEP" -eq 0 ]; then CUT=0000-00-00   # keep_days が 0 か null：全部残す
  else CUT=$(python3 -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=$KEEP)).isoformat())"); fi
  mkdir -p "$TMP/$cdir/$DIR"
  n=0
  for f in "$cdir/$DIR"/*; do
    [ -e "$f" ] || continue
    d=$(basename "$f"); d=${d:0:10}
    if [[ ! "$d" < "$CUT" ]]; then cp "$f" "$TMP/$cdir/$DIR/"; n=$((n + 1)); fi
  done
  if "$PY" -c "import PIL" 2>/dev/null; then "$PY" tools/share.py "$TMP/$cdir" --all --front > /dev/null || echo "[$cdir] 共有カードは作れませんでした（公開は続けます）"; fi
  echo "  $cid: 音声 $n 本（$CUT 以降）"
  total=$((total + n))
done
touch "$TMP/.nojekyll"                           # ファイルをそのまま配信する
cd "$TMP"
git init -q -b gh-pages
git add -A -f                                     # 音声も（.gitignore は main に入れないためのもの）
git -c user.name="$NAME" -c user.email="$EMAIL" commit -q -m "publish $(date +%F)"
git push -q -f "$REMOTE" gh-pages
echo "公開しました（gh-pages）：$(git ls-files | wc -l | tr -d ' ') ファイル、音声 $total 本"
