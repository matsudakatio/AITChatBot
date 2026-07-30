import os
import shutil
import time

from flask import Flask, request, jsonify
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM


# === 設定 =================================================================
TEXT_DIR = "data/texts"
PDF_DIR = "data/pdfs"
VECTOR_DIR = "vectorstore/index"

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "elyza-jp")

# data/texts を変えたあと再構築したい場合は環境変数で True にする
ALWAYS_REBUILD = os.getenv("ALWAYS_REBUILD", "false").lower() == "true"

# 開発時の検証用: True にすると回答に debug 情報（処理時間・出典チャンク・
# スコアなど）を付与する。リリース時は DEBUG=false（既定）にすれば
# 一切送られず、画面にもデバッグ表示は出ない。
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 検索で取得するチャンク数
TOP_K = int(os.getenv("TOP_K", "5"))
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

    print("資料を読み込んでベクトルDBを新規作成します")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    chunks = []

    if os.path.isdir(TEXT_DIR):
        for file in sorted(os.listdir(TEXT_DIR)):
            if file.lower().endswith(".txt"):
                path = os.path.join(TEXT_DIR, file)
                print(f"  読込(txt): {file}")
                with open(path, "r", encoding="utf-8") as f:
                    chunks.extend(
                        splitter.create_documents(
                            [f.read()], metadatas=[{"source": file}]
                        )
                    )

    if os.path.isdir(PDF_DIR):
        for file in sorted(os.listdir(PDF_DIR)):
            if file.lower().endswith(".pdf"):
                path = os.path.join(PDF_DIR, file)
                print(f"  読込(pdf): {file}")
                pages = PyPDFLoader(path).load()
                chunks.extend(splitter.split_documents(pages))

    if not chunks:
        raise RuntimeError(
            f"学習データが見つかりません ({TEXT_DIR} / {PDF_DIR})"
        )
    print(f"  チャンク数: {len(chunks)}")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(os.path.dirname(VECTOR_DIR), exist_ok=True)
    vectorstore.save_local(VECTOR_DIR)
    print("ベクトルDB作成完了")
    return vectorstore


vectorstore = load_or_create_vectorstore()
llm = OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_URL, temperature=0)


def answer_question(query: str):
    """質問に回答する。戻り値は (answer, debug)。
    debug は DEBUG=false のとき None。"""

    # --- 1) 検索（埋め込み生成 + 類似度検索） ---
    t0 = time.perf_counter()
    scored_docs = vectorstore.similarity_search_with_score(query, k=TOP_K)
    retrieval_sec = time.perf_counter() - t0

    docs = [d for d, _ in scored_docs]
    context = "\n".join(d.page_content for d in docs)

    prompt = f"""あなたは大学の学生窓口アシスタントです。
以下の【資料】だけを根拠に、質問へ日本語で具体的に答えてください。
資料に該当する情報があれば、必ずその内容を答えること。
どうしても資料に情報が無い場合のみ「資料には記載がありません」と答えてください。

【資料】
{context}

【質問】
{query}

【回答】"""

    # --- 2) 生成（LLM 呼び出し） ---
    t1 = time.perf_counter()
    answer = llm.invoke(prompt)
    llm_sec = time.perf_counter() - t1

    if not DEBUG:
        return answer, None

    # FAISS のスコアは L2 距離（小さいほど類似）
    sources = []
    for rank, (doc, score) in enumerate(scored_docs, start=1):
        content = doc.page_content
        sources.append(
            {
                "rank": rank,
                "source": doc.metadata.get("source", "?"),
                "page": doc.metadata.get("page"),
                "score": round(float(score), 4),
                "chars": len(content),
                "snippet": content[:200].replace("\n", " "),
            }
        )

    debug = {
        "timings_sec": {
            "retrieval": round(retrieval_sec, 3),
            "llm": round(llm_sec, 3),
            "total": round(retrieval_sec + llm_sec, 3),
        },
        "models": {"embed": EMBED_MODEL, "llm": LLM_MODEL},
        "retrieval": {
            "top_k": TOP_K,
            "context_chars": len(context),
            "prompt_chars": len(prompt),
            "query_chars": len(query),
        },
        "sources": sources,
    }
    return answer, debug


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        t_start = time.perf_counter()
        answer, debug = answer_question(query)
        payload = {"answer": answer}
        if debug is not None:
            # ルート全体（JSON化などを含む）の実測も入れておく
            debug["timings_sec"]["request_total"] = round(
                time.perf_counter() - t_start, 3
            )
            payload["debug"] = debug
        return jsonify(payload)
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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
