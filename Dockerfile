FROM python:3.11-slim

WORKDIR /app

# 必要なパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコード一式をコピー
COPY . .

# Flaskを外部からアクセス可能にする
CMD ["python", "app.py"]