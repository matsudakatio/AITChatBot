# AITChatBot

学内資料を使って質問に答えるローカルRAGチャットボット。

## アーキテクチャ

| 層 | 技術 | 役割 |
|---|---|---|
| フロント | HTML/CSS/JS | チャットUI（`static/`） |
| バックエンド | Flask + LangChain | API・RAG制御（`app.py`） |
| ベクトルDB | FAISS | 学内資料を意味検索可能な形で保存 |
| LLM | Ollama（`llama3` + `elyza-jp`） | 埋め込み生成・回答生成 |
| 基盤 | Docker Compose | 上記をコンテナで連携 |

`elyza-jp` は HuggingFace の `elyza/Llama-3-ELYZA-JP-8B-GGUF` を Ollama にプルしてエイリアスしたものを使う。`entrypoint.sh` が起動時に自動で準備する。

## 必要環境

- Docker Desktop
- Git

## セットアップ（共通）

```bash
git clone https://github.com/matsudakatio/AITChatBot.git
cd AITChatBot
cp .env.example .env
```

## 起動方法

### ローカル開発（自分のPC）

ホットリロード有効・コードを編集すると即反映：

```bash
docker compose up --build
```

ブラウザで <http://localhost:5001>。

### 研究室Mac（本番運用）

バックグラウンドで実行・自動再起動：

```bash
docker compose -f docker-compose.yml up -d --build
docker compose logs -f          # 起動状況を確認
```

初回はOllamaのモデルダウンロードで合計**10〜30分**かかる。完了するとログに以下が出る：

```
[entrypoint] elyza-jp のセットアップ完了
[entrypoint] Flaskアプリを起動します
 * Running on http://0.0.0.0:5000
```

## 家から研究室Macへ接続

Tailscale経由でSSHトンネルを張る：

```bash
# 研究室Mac側でTailscale IPを確認
tailscale ip -4

# 自分のPCで実行（IPは置き換える）
ssh -L 5001:localhost:5001 mizunolabo@100.x.x.x
```

接続したまま、ブラウザで <http://localhost:5001>。

## 開発ワークフロー

```bash
# 自分のPCで編集 → コミット
git add .
git commit -m "変更内容"
git push

# 研究室Macで反映
git pull
docker compose -f docker-compose.yml up -d --build
```

## ベクトルDBを作り直したい場合

`data/texts/` のテキストを変更したあとは：

```bash
docker compose -f docker-compose.yml down -v
docker compose -f docker-compose.yml up -d --build
```

## 停止

```bash
docker compose -f docker-compose.yml down
```

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| 初回起動が終わらない | モデルDL中。`docker compose logs -f web` で進捗を確認 |
| `model not found` | `docker exec aitchatbot-ollama-1 ollama list` で確認・再ビルド |
| メモリ不足で落ちる | Docker Desktop の Settings → Resources で割当メモリを増やす（推奨16GB以上） |
