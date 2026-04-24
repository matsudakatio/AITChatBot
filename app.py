from flask import Flask, request, jsonify
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import OllamaLLM

import os
import shutil

# static/index.html を使うために static_folder を宣言
app = Flask(__name__, static_folder="static", static_url_path="/static")

# === 設定 ==================================================
TEXT_DIR = "data/texts"
VECTOR_DIR = "vectorstore/index"

# 毎回ベクトルDBを作り直す場合は True
ALWAYS_REBUILD = True

# Dockerコンテナ間通信用のURL設定（ローカル実行時はlocalhostになる）
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# ===========================================================


# ---------- ベクトルDB作成 ----------
def load_or_create_vectorstore():
    # base_url を追加
    embeddings = OllamaEmbeddings(model="llama3", base_url=OLLAMA_URL)

    # ALWAYS_REBUILD の場合は毎回削除して作り直す
    if ALWAYS_REBUILD and os.path.exists(VECTOR_DIR):
        print("🔁 ALWAYS_REBUILD=True → 既存ベクトルDBを削除します...")
        shutil.rmtree(VECTOR_DIR)

    # 既存DBがあるならロード
    if os.path.exists(VECTOR_DIR):
        print("🌟 既存のベクトルDBを読み込み中...")
        return FAISS.load_local(
            VECTOR_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )

    # 新規作成
    print("📝 テキストを読み込んでベクトルDBを新規作成します...")
    docs = []

    # TEXT_DIR の中の .txt を全部読む
    for file in os.listdir(TEXT_DIR):
        if file.lower().endswith(".txt"):
            path = os.path.join(TEXT_DIR, file)
            print(f"  → {file} を読み込み中...")
            with open(path, "r", encoding="utf-8") as f:
                docs.append(f.read())

    # 分割
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200
    )
    chunks = splitter.create_documents(docs)

    # ベクトル化
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTOR_DIR)

    print("✅ ベクトルDB作成完了")
    return vectorstore


# 起動時にベクトルDB読み込み or 作成
vectorstore = load_or_create_vectorstore()


# ---------- 回答 ----------
def answer_question(query):
    # 質問に近い文章を検索
    docs = vectorstore.similarity_search(query, k=3)
    context = "\n".join([d.page_content for d in docs])

    # base_url を追加
    model = OllamaLLM(model="elyza-jp", base_url=OLLAMA_URL)

    prompt = f"""
以下の資料内容を使って質問に答えてください。

【資料】
{context}

【質問】
{query}
"""

    return model(prompt)


# ---------- API ----------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    answer = answer_question(data.get("query"))
    return jsonify({"answer": answer})


# ---------- UI表示 (static/index.html) ----------
@app.route("/")
def index():
    # static/index.html を返す
    return app.send_static_file("index.html")


if __name__ == "__main__":
    # ここが重要: host="0.0.0.0" を指定することでDocker外からアクセス可能になる
    app.run(host="0.0.0.0", port=5000, debug=True)