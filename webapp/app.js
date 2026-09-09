const tg = window.Telegram ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) {
    try { tg.setHeaderColor("#150f2e"); } catch (e) {}
  }
}

const initData = tg ? tg.initData : "";

// ============ DOM ============

const sidebar = document.getElementById("sidebar");
const backdrop = document.getElementById("backdrop");
const menuBtn = document.getElementById("menuBtn");
const newChatBtn = document.getElementById("newChatBtn");
const navItems = document.querySelectorAll(".nav-item");
const views = {
  chat: document.getElementById("chatView"),
  gallery: document.getElementById("galleryView"),
  help: document.getElementById("helpView"),
};
const topbarTitle = document.getElementById("topbarTitle");
const composer = document.getElementById("composer");

const messagesEl = document.getElementById("messages");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");

const modeRow = document.getElementById("modeRow");
const imageSettingsRow = document.getElementById("imageSettingsRow");
const videoModelRow = document.getElementById("videoModelRow");
const aspectRatioRow = document.getElementById("aspectRatioRow");

const balanceValue = document.getElementById("balanceValue");
const balanceValueTop = document.getElementById("balanceValueTop");

const stylesGrid = document.getElementById("stylesGrid");
const photoInput = document.getElementById("photoInput");

// ============ STATE ============

let currentMode = "text";
let currentAspect = "1:1";
let currentVideoModel = "wan";
let selectedStyleId = null;
let selectedStyleLabel = "";

const TITLES = {
  chat: "Suhbat",
  gallery: "Tayyor stillar",
  help: "Yordam",
};

// ============ SIDEBAR ============

function openSidebar() {
  sidebar.classList.add("open");
  backdrop.classList.add("visible");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  backdrop.classList.remove("visible");
}

menuBtn.addEventListener("click", openSidebar);
backdrop.addEventListener("click", closeSidebar);

// ============ VIEW SWITCHING ============

function switchView(name) {
  Object.entries(views).forEach(([key, el]) => {
    el.classList.toggle("active", key === name);
  });

  topbarTitle.textContent = TITLES[name];
  composer.classList.toggle("hidden", name !== "chat");

  navItems.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });

  closeSidebar();
}

navItems.forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

// ============ MODE SWITCHING ============

function setMode(mode) {
  currentMode = mode;

  document.querySelectorAll(".mode-chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.mode === mode);
  });

  imageSettingsRow.classList.toggle("hidden", mode !== "image");
  videoModelRow.classList.toggle("hidden", mode !== "video");

  const placeholders = {
    text: "Xabar yozing…",
    image: "Qanday rasm chizay? Masalan: yolg'iz archa, qor bosgan tog'…",
    video: "Video uchun tavsif yozing…",
    music: "Qanday musiqa yarataylik?",
    voice: "Ovozga aylantirish uchun matn yozing…",
  };

  messageInput.placeholder = placeholders[mode] || "Xabar yozing…";
}

modeRow.addEventListener("click", (e) => {
  const chip = e.target.closest(".mode-chip");
  if (chip) setMode(chip.dataset.mode);
});

aspectRatioRow.addEventListener("click", (e) => {
  const chip = e.target.closest("[data-aspect]");
  if (!chip) return;
  currentAspect = chip.dataset.aspect;
  aspectRatioRow.querySelectorAll(".mini-chip").forEach((c) =>
    c.classList.toggle("active", c === chip)
  );
});

videoModelRow.addEventListener("click", (e) => {
  const chip = e.target.closest("[data-video-model]");
  if (!chip) return;
  currentVideoModel = chip.dataset.videoModel;
  videoModelRow.querySelectorAll(".mini-chip").forEach((c) =>
    c.classList.toggle("active", c === chip)
  );
});

// ============ CHAT RENDERING ============

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendUserBubble(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg msg-user";
  wrap.innerHTML = `<div class="bubble"></div>`;
  wrap.querySelector(".bubble").textContent = text;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function appendPendingBubble(label) {
  const wrap = document.createElement("div");
  wrap.className = "msg msg-bot";
  wrap.innerHTML = `
    <div class="bubble pending">
      <span class="dot-pulse"></span> ${label}
    </div>
  `;
  messagesEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function resolvePendingAsText(wrapEl, text) {
  wrapEl.querySelector(".bubble").outerHTML = `<div class="bubble"></div>`;
  wrapEl.querySelector(".bubble").textContent = text;
  scrollToBottom();
}

function resolvePendingAsImage(wrapEl, url) {
  wrapEl.querySelector(".bubble").outerHTML =
    `<div class="bubble"><img src="${url}" alt="Natija" /></div>`;
  scrollToBottom();
}

function resolvePendingAsVideo(wrapEl, url) {
  wrapEl.querySelector(".bubble").outerHTML =
    `<div class="bubble"><video src="${url}" controls playsinline></video></div>`;
  scrollToBottom();
}

function resolvePendingAsAudio(wrapEl, url) {
  wrapEl.querySelector(".bubble").outerHTML =
    `<div class="bubble"><audio src="${url}" controls></audio></div>`;
  scrollToBottom();
}

function resolvePendingAsError(wrapEl, message) {
  wrapEl.querySelector(".bubble").outerHTML =
    `<div class="bubble error-bubble"></div>`;
  wrapEl.querySelector(".bubble").textContent = "⚠️ " + message;
  scrollToBottom();
}

function updateBalance(value) {
  balanceValue.textContent = value;
  balanceValueTop.textContent = value;
}

// ============ SEND LOGIC ============

async function handleSend() {
  const text = messageInput.value.trim();
  if (!text) return;

  messageInput.value = "";
  messageInput.style.height = "auto";
  sendBtn.disabled = true;

  appendUserBubble(text);

  try {
    if (currentMode === "text") {
      const pending = appendPendingBubble("Yozmoqda…");
      const form = new FormData();
      form.append("init_data", initData);
      form.append("message", text);
      const resp = await fetch("/api/chat", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Xatolik");
      resolvePendingAsText(pending, data.reply);
      updateBalance(data.balance);

    } else if (currentMode === "image") {
      const pending = appendPendingBubble("Rasm yaratilmoqda…");
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      form.append("aspect_ratio", currentAspect);
      const resp = await fetch("/api/generate-image", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Xatolik");
      resolvePendingAsImage(pending, data.image_url);
      updateBalance(data.balance);

    } else if (currentMode === "video") {
      const pending = appendPendingBubble("Video yaratilmoqda (biroz uzoqroq davom etadi)…");
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      form.append("model_key", currentVideoModel);
      const resp = await fetch("/api/generate-video", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Xatolik");
      resolvePendingAsVideo(pending, data.video_url);
      updateBalance(data.balance);

    } else if (currentMode === "music") {
      const pending = appendPendingBubble("Musiqa yaratilmoqda…");
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      const resp = await fetch("/api/generate-music", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Xatolik");
      resolvePendingAsAudio(pending, data.audio_url);
      updateBalance(data.balance);

    } else if (currentMode === "voice") {
      const pending = appendPendingBubble("Ovoz yaratilmoqda…");
      const form = new FormData();
      form.append("init_data", initData);
      form.append("text", text);
      const resp = await fetch("/api/generate-voice", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Xatolik");
      const audioUrl = "data:audio/mpeg;base64," + data.audio_base64;
      resolvePendingAsAudio(pending, audioUrl);
      updateBalance(data.balance);
    }

    if (tg && tg.HapticFeedback) {
      tg.HapticFeedback.notificationOccurred("success");
    }
  } catch (e) {
    const bubbles = messagesEl.querySelectorAll(".msg-bot .bubble.pending");
    const lastPending = bubbles[bubbles.length - 1];
    if (lastPending) {
      resolvePendingAsError(lastPending.closest(".msg"), e.message);
    }
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", handleSend);

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 110) + "px";
});

// ============ YANGI SUHBAT ============

newChatBtn.addEventListener("click", async () => {
  try {
    const form = new FormData();
    form.append("init_data", initData);
    await fetch("/api/new-chat", { method: "POST", body: form });
  } catch (e) {
    console.error(e);
  }

  messagesEl.innerHTML = `
    <div class="msg msg-bot">
      <div class="bubble">Yangi suhbat boshlandi! 👋 Nima haqida gaplashamiz?</div>
    </div>
  `;
  switchView("chat");
});

// ============ MIKROFON (dikтация, mavjud bo'lsa) ============

const SpeechRecognitionCtor =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognitionCtor) {
  micBtn.classList.remove("hidden");

  const recognition = new SpeechRecognitionCtor();
  recognition.lang = "uz-UZ";
  recognition.interimResults = false;

  let isRecording = false;

  micBtn.addEventListener("click", () => {
    if (isRecording) {
      recognition.stop();
      return;
    }
    try {
      recognition.start();
      isRecording = true;
      micBtn.classList.add("recording");
    } catch (e) {
      console.error(e);
    }
  });

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    messageInput.value = (messageInput.value + " " + transcript).trim();
  });

  recognition.addEventListener("end", () => {
    isRecording = false;
    micBtn.classList.remove("recording");
  });

  recognition.addEventListener("error", () => {
    isRecording = false;
    micBtn.classList.remove("recording");
  });
}

// ============ GALEREYA (Tayyor stillar) ============

async function loadStyles() {
  try {
    const resp = await fetch("/api/styles");
    const styles = await resp.json();

    stylesGrid.innerHTML = "";

    styles.forEach((style, index) => {
      const card = document.createElement("button");
      card.className = `style-card hue-${index % 6}`;
      card.type = "button";

      const emojiMatch = style.label.match(/\p{Emoji}/u);
      const emoji = emojiMatch ? emojiMatch[0] : "🎨";
      const text = style.label.replace(/\p{Emoji}/gu, "").trim();

      card.innerHTML = `
        <div class="style-thumb">${emoji}</div>
        <div class="style-label">${text}</div>
      `;

      card.addEventListener("click", () => {
        selectedStyleId = style.id;
        selectedStyleLabel = style.label;
        photoInput.click();
      });

      stylesGrid.appendChild(card);
    });
  } catch (e) {
    console.error("Stillarni yuklab bo'lmadi", e);
  }
}

photoInput.addEventListener("change", async () => {
  const file = photoInput.files[0];
  if (!file || !selectedStyleId) return;

  switchView("chat");
  appendUserBubble(`🖼 ${selectedStyleLabel}`);
  const pending = appendPendingBubble("Stil qo'llanmoqda…");

  try {
    const form = new FormData();
    form.append("init_data", initData);
    form.append("style_id", selectedStyleId);
    form.append("photo", file);

    const resp = await fetch("/api/apply-style", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Xatolik");

    resolvePendingAsImage(pending, data.result_url);
    updateBalance(data.balance);
  } catch (e) {
    resolvePendingAsError(pending, e.message);
  } finally {
    photoInput.value = "";
    selectedStyleId = null;
  }
});

// ============ BOSHLANG'ICH YUKLASH ============

async function loadBalance() {
  if (!initData) {
    updateBalance("—");
    return;
  }

  try {
    const resp = await fetch("/api/balance?init_data=" + encodeURIComponent(initData));
    if (!resp.ok) throw new Error("balance so'rovi muvaffaqiyatsiz");
    const data = await resp.json();
    updateBalance(data.balance);
  } catch (e) {
    updateBalance("—");
  }
}

loadStyles();
loadBalance();
