import os
import shutil

from flask import Flask, request, jsonify
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM


# === 設定 =================================================================
TEXT_DIR = "data/texts"
VECTOR_DIR = "vectorstore/index"

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "llama3")
LLM_MODEL = os.getenv("LLM_MODEL", "elyza-jp")

# data/texts を変えたあと再構築したい場合は環境変数で True にする
ALWAYS_REBUILD = os.getenv("ALWAYS_REBUILD", "false").lower() == "true"
# =========================================================================


app = Flask(__name__, static_folder="static", static_url_path="/static")


def load_or_create_vectorstore():
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)

    if ALWAYS_REBUILD and os.path.exists(VECTOR_DIR):
        print("ALWAYS_REBUILD=True なので既存のベクトルDBを削除します")
        shutil.rmtree(VECTOR_DIR)

    if os.path.exists(VECTOR_DIR):
        print("既存のベクトルDBを読み込みます")
        return FAISS.load_local(
            VECTOR_DIR, embeddings, allow_dangerous_deserialization=True
        )

    print("テキストを読み込んでベクトルDBを新規作成します")
    docs = []
    for file in sorted(os.listdir(TEXT_DIR)):
        if file.lower().endswith(".txt"):
            path = os.path.join(TEXT_DIR, file)
            print(f"  読込: {file}")
            with open(path, "r", encoding="utf-8") as f:
                docs.append(f.read())

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    chunks = splitter.create_documents(docs)

    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(os.path.dirname(VECTOR_DIR), exist_ok=True)
    vectorstore.save_local(VECTOR_DIR)
    print("ベクトルDB作成完了")
    return vectorstore


vectorstore = load_or_create_vectorstore()
llm = OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_URL)


def answer_question(query: str) -> str:
    docs = vectorstore.similarity_search(query, k=3)
    context = "\n".join(d.page_content for d in docs)

    prompt = f"""以下の資料内容を使って質問に答えてください。
資料に書かれていないことは推測せず「資料には記載がありません」と答えてください。

【資料】
{context}

【質問】
{query}

【回答】"""

    return llm.invoke(prompt)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        return jsonify({"answer": answer_question(query)})
    except Exception as e:
        app.logger.exception("ask failed")
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
