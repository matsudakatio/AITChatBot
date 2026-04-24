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

// 送信処理
async function sendMessage() {
    const text = input.value.trim();
    if (text === "") return;

    addMessage(text, true);
    input.value = "";

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: text }),
        });

        const data = await res.json();

        if (data.answer) {
            addMessage(data.answer, false);
        } else {
            addMessage("（返信なし）", false);
        }
    } catch (err) {
        addMessage("（サーバーに接続できません）", false);
    }
}

// ボタン
sendBtn.addEventListener("click", sendMessage);

// Enterキーで送信
input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});
