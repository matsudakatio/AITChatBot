#!/bin/sh
# Ollamaの起動を待ってからモデルをダウンロードし、アプリを起動する

echo "Ollamaの起動を待っています..."
until curl -sf "${OLLAMA_HOST:-http://ollama:11434}/api/tags" > /dev/null 2>&1; do
  sleep 2
done
echo "Ollama 起動確認OK"

# モデルが存在しない場合のみダウンロード
for MODEL in llama3 elyza-jp; do
  if ! curl -sf "${OLLAMA_HOST:-http://ollama:11434}/api/tags" | grep -q "\"${MODEL}\""; then
    echo "${MODEL} をダウンロード中... (数分かかる場合があります)"
    curl -sf "${OLLAMA_HOST:-http://ollama:11434}/api/pull" \
      -d "{\"name\":\"${MODEL}\"}" > /dev/null
    echo "${MODEL} ダウンロード完了"
  else
    echo "${MODEL} は既に存在します"
  fi
done

exec python app.py
