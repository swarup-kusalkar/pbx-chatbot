// ─── State ────────────────────────────────────────────────

let currentSessionId = localStorage.getItem("pbx_session_id") || null;
let isLoading = false;
let currentArticleForModal = null;

// ─── Speech Recognition State ─────────────────────────────
let recognition = null;
let isRecording = false;
let speechInterimText = "";  // live interim result
let speechFinalText = "";    // accumulated finals before stopping

// ─── Initialization ────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
    initSession();
    initEventListeners();
    loadSessions();
    loadArticles();
});

// ─── Session Management ─────────────────────────────────────

function initSession() {
    if (!currentSessionId) {
        currentSessionId = generateUUID();
        localStorage.setItem("pbx_session_id", currentSessionId);
        createSession(currentSessionId);
    }
    loadHistory(currentSessionId);
}

function generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

async function createSession(sessionId) {
    try {
        await fetch("/api/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch (e) {
        console.error("Failed to create session:", e);
    }
}

// ─── Event Listeners ─────────────────────────────────────────

function initEventListeners() {
    // Tabs
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // New Chat
    document.getElementById("new-chat-btn").addEventListener("click", newChat);

    // Export
    document.getElementById("export-btn").addEventListener("click", exportChat);

    // Clear
    document.getElementById("clear-btn").addEventListener("click", clearChat);

    // Send button
    document.getElementById("send-btn").addEventListener("click", sendMessage);

    // Mic button
    document.getElementById("mic-btn").addEventListener("click", toggleMicRecording);


    // Enter to send (Shift+Enter for newline)
    document.getElementById("message-input").addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    const input = document.getElementById("message-input");
    input.addEventListener("input", () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 150) + "px";
        updateCharCounter();
        updateSendButton();
    });

    // Quick question buttons
    document.querySelectorAll(".quick-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.getElementById("message-input").value = btn.dataset.question;
            updateCharCounter();
            updateSendButton();
            sendMessage();
        });
    });

    // Modal
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("article-modal").addEventListener("click", e => {
        if (e.target.id === "article-modal") closeModal();
    });
    document.getElementById("ask-about-article").addEventListener("click", () => {
        if (currentArticleForModal) {
            closeModal();
            document.getElementById("message-input").value = currentArticleForModal.question;
            updateCharCounter();
            updateSendButton();
            sendMessage();
        }
    });

    // Session list clicks
    document.getElementById("sessions-list").addEventListener("click", e => {
        const item = e.target.closest(".session-item");
        if (item) {
            switchSession(item.dataset.sessionId);
        }
    });

    // Article list clicks
    document.getElementById("articles-list").addEventListener("click", e => {
        const item = e.target.closest(".article-item");
        if (item) {
            openArticleModal(item.dataset.id);
        }
    });
}

// ─── Tab Switching ──────────────────────────────────────────

function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add("active");
    document.getElementById(`tab-${tab}`).classList.add("active");
}

// ─── Load Functions ─────────────────────────────────────────

async function loadSessions() {
    try {
        const res = await fetch("/api/sessions");
        const data = await res.json();
        if (!data.success) return;

        const list = document.getElementById("sessions-list");
        list.innerHTML = "";

        data.data.forEach(session => {
            const div = document.createElement("div");
            div.className = `session-item${session.id === currentSessionId ? " active" : ""}`;
            div.dataset.sessionId = session.id;
            div.innerHTML = `
                <div class="session-title">${escapeHtml(session.title || "New chat")}</div>
                <div class="session-time">${formatRelativeTime(session.updated_at)}</div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to load sessions:", e);
    }
}

async function loadArticles() {
    try {
        const res = await fetch("/api/knowledge");
        const data = await res.json();
        if (!data.success) return;

        const list = document.getElementById("articles-list");
        list.innerHTML = "";

        data.data.forEach(article => {
            const div = document.createElement("div");
            div.className = "article-item";
            div.dataset.id = article.id;
            div.innerHTML = `
                <div class="article-topic">${escapeHtml(article.topic)}</div>
                <div class="article-question">${escapeHtml(article.question)}</div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to load articles:", e);
    }
}

async function loadHistory(sessionId) {
    try {
        const res = await fetch(`/api/history/${sessionId}`);
        const data = await res.json();

        const welcome = document.getElementById("welcome-state");
        const chatArea = document.getElementById("chat-area");
        const messages = document.getElementById("messages");

        messages.innerHTML = "";
        welcome.classList.add("hidden");
        chatArea.classList.add("active");

        if (data.success && data.data && data.data.messages.length > 0) {
            data.data.messages.forEach(msg => {
                addMessageToUI(msg.role, msg.content, msg.created_at);
            });
            smartScrollToBottom();
        }

        updateSendButton();
    } catch (e) {
        console.error("Failed to load history:", e);
        showWelcome();
    }
}

// ─── Chat Functions ──────────────────────────────────────────

async function sendMessage() {
    if (isLoading) return;

    const input = document.getElementById("message-input");
    const message = input.value.trim();

    if (!message) return;

    isLoading = true;
    updateSendButton();
    showThinking(true);

    if (document.getElementById("welcome-state").classList.contains("hidden") === false) {
        showChat();
    }

    addMessageToUI("user", message);
    input.value = "";
    input.style.height = "auto";
    updateCharCounter();
    smartScrollToBottom();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, session_id: currentSessionId })
        });

        const data = await res.json();

        if (data.success) {
            addMessageToUI("assistant", data.data.reply, null, data.data.retrieved_topics, data.data.llm_used);
            loadSessions();
        } else {
            addMessageToUI("assistant", `Error: ${data.error?.message || "Something went wrong. Please try again."}`, null, [], null, true);
        }
    } catch (e) {
        addMessageToUI("assistant", "Unable to reach the server. Check your connection.", null, [], null, true);
    }

    isLoading = false;
    updateSendButton();
    showThinking(false);
    smartScrollToBottom();
}

// ─── Message Rendering ───────────────────────────────────────

function addMessageToUI(role, content, timestamp = null, sources = [], llmUsed = null, isError = false) {
    const messages = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}${isError ? " error" : ""}`;

    const time = timestamp ? formatTime(new Date(timestamp)) : formatTime(new Date());

    if (role === "assistant") {
        const renderedContent = DOMPurify.sanitize(marked.parse(content));

        msgDiv.innerHTML = `
            ${sources.length > 0 ? `
                <div class="sources">
                    <div class="sources-list">
                        ${[...new Set(sources)].map(s => `<span class="source-badge">${escapeHtml(s)}</span>`).join("")}
                    </div>
                </div>
            ` : ""}
            <div class="message-bubble">${renderedContent}</div>
            <div class="message-time">${time}${llmUsed ? ` · ${llmUsed}` : ""}</div>
        `;
    } else {
        msgDiv.innerHTML = `
            <div class="message-bubble">${escapeHtml(content)}</div>
            <div class="message-time">${time}</div>
        `;
    }

    messages.appendChild(msgDiv);
}

// ─── UI Helpers ─────────────────────────────────────────────

function showWelcome() {
    document.getElementById("welcome-state").classList.remove("hidden");
    document.getElementById("chat-area").classList.remove("active");
}

function showChat() {
    document.getElementById("welcome-state").classList.add("hidden");
    document.getElementById("chat-area").classList.add("active");
}

function showThinking(show) {
    document.getElementById("thinking-indicator").classList.toggle("active", show);
    smartScrollToBottom();
}

function updateSendButton() {
    const input = document.getElementById("message-input");
    const btn = document.getElementById("send-btn");
    btn.disabled = !input.value.trim() || isLoading;
}

function updateCharCounter() {
    const input = document.getElementById("message-input");
    const counter = document.getElementById("char-counter");
    const len = input.value.length;
    counter.textContent = `${len}/2000`;
    counter.classList.toggle("warning", len >= 1900);
}

function smartScrollToBottom() {
    const chatArea = document.getElementById("chat-area");
    const isNearBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 100;
    if (isNearBottom) {
        chatArea.scrollTop = chatArea.scrollHeight;
    }
}

// ─── Session Actions ─────────────────────────────────────────

async function newChat() {
    currentSessionId = generateUUID();
    localStorage.setItem("pbx_session_id", currentSessionId);
    await createSession(currentSessionId);
    document.getElementById("messages").innerHTML = "";
    showWelcome();
    loadSessions();
    updateSendButton();
}

async function switchSession(sessionId) {
    if (sessionId === currentSessionId) return;
    currentSessionId = sessionId;
    localStorage.setItem("pbx_session_id", sessionId);
    await loadHistory(sessionId);
    loadSessions();
}

async function clearChat() {
    if (!currentSessionId) return;
    try {
        await fetch(`/api/sessions/${currentSessionId}`, { method: "DELETE" });
        document.getElementById("messages").innerHTML = "";
        showWelcome();
        loadSessions();
        await createSession(currentSessionId);
    } catch (e) {
        console.error("Failed to clear chat:", e);
    }
}

async function exportChat() {
    if (!currentSessionId) return;
    try {
        const res = await fetch(`/api/export/${currentSessionId}`);
        const text = await res.text();
        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `pbx-chat-${currentSessionId.slice(0, 8)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Failed to export:", e);
    }
}

// ─── Article Modal ──────────────────────────────────────────

async function openArticleModal(articleId) {
    try {
        const res = await fetch("/api/knowledge");
        const data = await res.json();
        if (!data.success) return;

        const article = data.data.find(a => a.id == articleId);
        if (!article) return;

        currentArticleForModal = { id: article.id, question: article.question };

        document.getElementById("modal-title").textContent = article.topic;
        document.getElementById("modal-body").innerHTML = DOMPurify.sanitize(marked.parse(article.answer));
        document.getElementById("article-modal").classList.add("active");
    } catch (e) {
        console.error("Failed to load article:", e);
    }
}

function closeModal() {
    document.getElementById("article-modal").classList.remove("active");
    currentArticleForModal = null;
}

// ─── Utilities ──────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatRelativeTime(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
}

// ─── Speech Recognition ──────────────────────────────────────

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        showMicError("Speech Recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
        return false;
    }

    if (!recognition) {
        recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isRecording = true;
            const micBtn = document.getElementById("mic-btn");
            micBtn.classList.add("recording");
            micBtn.title = "Recording… click to stop";
        };

        recognition.onresult = onSpeechResult;

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                showMicError("Microphone access blocked. Please allow microphone access in your browser settings.");
            } else if (event.error !== "no-speech") {
                showMicError(`Speech error: ${event.error}`);
            }
            stopRecording(true);
        };

        recognition.onend = () => {
            if (isRecording) {
                commitTranscript();
                resetMicButton();
                isRecording = false;
            }
        };
    }

    return true;
}

async function toggleMicRecording() {
    if (isLoading) return;

    const micBtn = document.getElementById("mic-btn");

    if (!isRecording) {
        // Request microphone permission explicitly to trigger browser permission dialog
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // Stop temp tracks now that permission is granted
                stream.getTracks().forEach(track => track.stop());
            } catch (err) {
                console.error("Microphone permission error:", err);
                showMicError("Microphone access denied. Please allow microphone permission in your browser address bar.");
                return;
            }
        }

        // Init recognition
        if (!initSpeechRecognition()) return;

        speechFinalText = document.getElementById("message-input").value;
        speechInterimText = "";

        try {
            isRecording = true;
            micBtn.classList.add("recording");
            micBtn.title = "Recording… click to stop";

            recognition.start();
        } catch (e) {
            console.warn("Speech recognition start failed or already active:", e);
            try {
                recognition.stop();
            } catch (err) {}
            
            setTimeout(() => {
                try {
                    recognition.start();
                } catch (err2) {
                    showMicError("Could not start microphone speech recognition.");
                    stopRecording(true);
                }
            }, 150);
        }
    } else {
        stopRecording();
    }
}

function onSpeechResult(event) {
    const input = document.getElementById("message-input");
    let interim = "";
    let finalChunk = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
            finalChunk += transcript;
        } else {
            interim += transcript;
        }
    }

    if (finalChunk) {
        speechFinalText = (speechFinalText.trimEnd() + " " + finalChunk.trimStart()).trim();
    }
    speechInterimText = interim;

    // Put current transcribed text into chat input text box
    const fullText = speechInterimText
        ? (speechFinalText ? speechFinalText + " " + speechInterimText : speechInterimText)
        : speechFinalText;

    input.value = fullText;

    // Auto-resize textarea
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
    updateCharCounter();
    updateSendButton();
}

function stopRecording(forceReset = false) {
    isRecording = false;

    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {}
    }

    if (!forceReset) {
        commitTranscript();
    }

    resetMicButton();
}

function commitTranscript() {
    const input = document.getElementById("message-input");
    const textToCommit = (speechInterimText
        ? (speechFinalText ? speechFinalText + " " + speechInterimText : speechInterimText)
        : speechFinalText).trim();

    if (textToCommit) {
        input.value = textToCommit;
    }
    
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 150) + "px";
    updateCharCounter();
    updateSendButton();
    
    // Focus input box
    input.focus();
}

function resetMicButton() {
    const micBtn = document.getElementById("mic-btn");
    micBtn.classList.remove("recording");
    micBtn.title = "Click to speak";
    isRecording = false;
    speechFinalText = "";
    speechInterimText = "";
}

function showMicError(message) {
    let errDiv = document.getElementById("mic-error-toast");
    if (errDiv) errDiv.remove();
    
    errDiv = document.createElement("div");
    errDiv.id = "mic-error-toast";
    errDiv.style.cssText = "position: fixed; bottom: 90px; right: 24px; background: #ef4444; color: white; padding: 12px 18px; border-radius: 10px; font-size: 13px; font-weight: 500; z-index: 9999; box-shadow: 0 4px 16px rgba(0,0,0,0.4); animation: fadeIn 0.3s ease; display: flex; align-items: center; gap: 8px;";
    errDiv.innerHTML = `<span>🎙️</span> <span>${escapeHtml(message)}</span>`;
    
    document.body.appendChild(errDiv);
    setTimeout(() => {
        if (errDiv && errDiv.parentNode) {
            errDiv.parentNode.removeChild(errDiv);
        }
    }, 5000);
}
