const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const chatBox = document.getElementById("chat-box");

// メッセージ追加
function addMessage(text, isUser) {
    const msg = document.createElement("div");
    msg.classList.add("message", isUser ? "me" : "other");
    msg.textContent = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// デバッグ情報の表示（サーバーが DEBUG=true のときだけ debug が届く）
function addDebug(debug) {
    if (!debug) return;

    const t = debug.timings_sec || {};
    const m = debug.models || {};
    const r = debug.retrieval || {};
    const sources = debug.sources || [];

    const panel = document.createElement("details");
    panel.classList.add("debug-panel");
    panel.open = true;

    const summary = document.createElement("summary");
    summary.textContent =
        `🔍 デバッグ情報  合計 ${t.total ?? "-"}s ` +
        `（検索 ${t.retrieval ?? "-"}s / 生成 ${t.llm ?? "-"}s）`;
    panel.appendChild(summary);

    // 数値サマリー（チップ表示）
    const stats = document.createElement("div");
    stats.classList.add("debug-stats");
    const chips = [
        ["検索", `${t.retrieval ?? "-"} s`],
        ["生成(LLM)", `${t.llm ?? "-"} s`],
        ["処理合計", `${t.total ?? "-"} s`],
        ["リクエスト全体", `${t.request_total ?? "-"} s`],
        ["埋め込み", m.embed ?? "-"],
        ["LLM", m.llm ?? "-"],
        ["top_k", r.top_k ?? "-"],
        ["文脈文字数", r.context_chars ?? "-"],
        ["プロンプト文字数", r.prompt_chars ?? "-"],
    ];
    for (const [label, value] of chips) {
        const chip = document.createElement("div");
        chip.classList.add("debug-chip");
        chip.innerHTML =
            `<span class="debug-chip-label">${label}</span>` +
            `<span class="debug-chip-value">${value}</span>`;
        stats.appendChild(chip);
    }
    panel.appendChild(stats);

    // 出典チャンク一覧
    if (sources.length) {
        const title = document.createElement("div");
        title.classList.add("debug-section-title");
        title.textContent = `参照した資料チャンク（${sources.length}件・スコアが小さいほど類似）`;
        panel.appendChild(title);

        for (const s of sources) {
            const item = document.createElement("div");
            item.classList.add("debug-source");
            const page = s.page != null ? ` p.${s.page}` : "";
            item.innerHTML =
                `<div class="debug-source-head">` +
                `<span class="debug-rank">#${s.rank}</span>` +
                `<span class="debug-src-name">${s.source}${page}</span>` +
                `<span class="debug-score">score ${s.score}</span>` +
                `<span class="debug-src-chars">${s.chars}文字</span>` +
                `</div>` +
                `<div class="debug-snippet"></div>`;
            item.querySelector(".debug-snippet").textContent = s.snippet;
            panel.appendChild(item);
        }
    }

    chatBox.appendChild(panel);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 「考えています」の経過時間インジケーター
function startThinking() {
    const el = document.createElement("div");
    el.classList.add("message", "other", "thinking");
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;

    const started = Date.now();
    const render = () => {
        const sec = ((Date.now() - started) / 1000).toFixed(1);
        el.textContent = `回答を考えています…（${sec}秒）`;
    };
    render();
    const timer = setInterval(render, 100);

    // 停止して要素を消す
    return () => {
        clearInterval(timer);
        el.remove();
    };
}

// 送信処理
async function sendMessage() {
    const text = input.value.trim();
    if (text === "") return;

    addMessage(text, true);
    input.value = "";

    const stopThinking = startThinking();
    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: text }),
        });

        const data = await res.json();
        stopThinking();

        if (data.answer) {
            addMessage(data.answer, false);
        } else {
            addMessage("（返信なし）", false);
        }

        // 開発時（サーバーが DEBUG=true）のみ検証用情報を表示
        addDebug(data.debug);
    } catch (err) {
        stopThinking();
        addMessage("（サーバーに接続できません）", false);
    }
}

// ボタン
sendBtn.addEventListener("click", sendMessage);

// Enterキーで送信
input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});
