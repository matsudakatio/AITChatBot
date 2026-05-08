# AITChatBot

## 構成

```
AITChatBot/
├── app.py                      # Flaskアプリ本体
├── data/texts/                 # 学内資料テキスト
├── static/                     # フロントエンド
├── utils/
├── Dockerfile
├── docker-compose.yml          # 本番（研究室Mac）用
├── docker-compose.override.yml # ローカル開発用（自動適用）
└── entrypoint.sh               # 起動時にOllamaモデルを自動DL
```

---

## 開発メンバーのセットアップ

### 前提
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) がインストール済み
- Git が使える

### 手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/matsudakatio/AITChatBot.git
cd AITChatBot

# 2. 環境設定（必要なら変更）
cp .env.example .env

# 3. 起動（初回はOllamaモデルのダウンロードで数分かかる）
docker compose up --build

# 4. ブラウザで確認
# http://localhost:5001
```

### 開発時のワークフロー

```bash
# コードを変更 → 自動でコンテナに反映（override.ymlのvolumeマウントのおかげ）
# app.py を変更した場合はFlaskが自動リロード

# コンテナのログを見る
docker compose logs -f web

# 停止
docker compose down
```

---

## 研究室Mac（本番）での運用

### 起動方法

```bash
# overrideなし（本番モード）で起動
docker compose -f docker-compose.yml up -d --build

# ログ確認
docker compose logs -f

# 停止
docker compose down
```

### 家・外出先からアクセスする方法

研究室Macに SSH でアクセスできる場合、**ローカルポートフォワーディング**で自分のPCからアクセスできる：

```bash
# ターミナルで実行（研究室MacのIPアドレスを入力）
ssh -L 5001:localhost:5001 ユーザー名@研究室MacのIPアドレス

# 接続後、ブラウザで
# http://localhost:5001 にアクセスするとチャットボットが使える
```

---

## Gitでのコード管理

```bash
# 変更をコミット・プッシュ
git add .
git commit -m "変更内容の説明"
git push

# 研究室Mac側で最新コードを取得して再起動
git pull
docker compose -f docker-compose.yml up -d --build
```

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| 起動に時間がかかる | 初回はOllamaモデル（数GB）をダウンロード中。ログで確認 |
| `http://localhost:5001` につながらない | `docker compose ps` でコンテナが起動中か確認 |
| モデルが見つからないエラー | `docker compose restart web` で再起動 |
