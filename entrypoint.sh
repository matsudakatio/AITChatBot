#!/bin/sh
set -e

OLLAMA="${OLLAMA_HOST:-http://ollama:11434}"
EMBED_MODEL="${EMBED_MODEL:-llama3}"
LLM_MODEL="${LLM_MODEL:-elyza-jp}"
ELYZA_SOURCE="${ELYZA_SOURCE:-hf.co/elyza/Llama-3-ELYZA-JP-8B-GGUF:Q4_K_M}"

echo "[entrypoint] Ollamaの起動を待ちます: $OLLAMA"
until curl -sf "$OLLAMA/api/tags" > /dev/null 2>&1; do
  sleep 2
done
echo "[entrypoint] Ollama 起動確認OK"

# モデル存在チェック
has_model() {
  curl -sf "$OLLAMA/api/tags" | grep -q "\"name\":\"$1"
}

# モデルプル
pull_model() {
  echo "[entrypoint] $1 をダウンロード中..."
  curl -sN "$OLLAMA/api/pull" -d "{\"name\":\"$1\",\"stream\":false}" > /dev/null
  echo "[entrypoint] $1 ダウンロード完了"
}

# 埋め込み用 llama3
if has_model "$EMBED_MODEL"; then
  echo "[entrypoint] $EMBED_MODEL は既に存在します"
else
  pull_model "$EMBED_MODEL"
fi

# 回答用 elyza-jp（HuggingFaceから取得しエイリアス作成）
if has_model "$LLM_MODEL"; then
  echo "[entrypoint] $LLM_MODEL は既に存在します"
else
  if ! has_model "$ELYZA_SOURCE"; then
    pull_model "$ELYZA_SOURCE"
  fi
  echo "[entrypoint] $ELYZA_SOURCE を $LLM_MODEL という名前にコピーします"
  curl -sf "$OLLAMA/api/copy" \
    -d "{\"source\":\"$ELYZA_SOURCE\",\"destination\":\"$LLM_MODEL\"}" > /dev/null
  echo "[entrypoint] $LLM_MODEL のセットアップ完了"
fi

echo "[entrypoint] Flaskアプリを起動します"
exec python app.py
