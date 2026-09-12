const tg = window.Telegram ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) {
    try { tg.setHeaderColor("#150f2e"); } catch (e) {}
  }
}

const initData = tg ? tg.initData : "";

// ============ TARJIMALAR ============
// MUHIM: bu lug'at bot.py/i18n.py'dagi matnlarga ohangdosh
// qilib yozilgan — bot qaysi tilni tanlagan bo'lsa (get_lang),
// Mini App ham o'sha tilda ochiladi (/api/lang orqali so'raladi).

const MINIAPP_I18N = {
  uz: {
    newChat: "Yangi suhbat",
    navChat: "Suhbat",
    navGallery: "Tayyor stillar",
    navHelp: "Yordam",
    titleChat: "Suhbat",
    titleGallery: "Tayyor stillar",
    titleHelp: "Yordam",
    welcomeMessage: "Salom! 👋 Men MUBORAKXON. Pastdagi rejimlardan birini tanlang va menga yozing — matn, rasm, video, musiqa yoki ovoz yarataman.",
    galleryLead: "Rasmingizni tanlang, stilni bosing — qolganini biz qilamiz.",
    helpTitle: "Qanday ishlaydi",
    helpLineText: "💬 Matn — MUBORAKXON bilan oddiy suhbat.",
    helpLineImage: "🎨 Rasm — yozgan tavsifingiz asosida rasm yaratadi.",
    helpLineVideo: "🎬 Video — tavsifdan qisqa video yaratadi.",
    helpLineMusic: "🎵 Musiqa — tavsifdan musiqa yaratadi.",
    helpLineVoice: "🔊 Ovoz — matningizni ovozga aylantiradi.",
    helpLineStyles: "🖼 Tayyor stillar — o'z rasmingizga tayyor stil qo'llaydi.",
    helpNote: "Har bir amal balansingizdan coin yechadi — narxlarni pastdagi balans chipida ko'rasiz.",
    formatLabel: "Format",
    modelLabel: "Model",
    videoModelWan: "🟢 Wan (arzon)",
    videoModelKling: "🔵 Kling (sifatli)",
    modeText: "💬 Matn",
    modeImage: "🎨 Rasm",
    modeVideo: "🎬 Video",
    modeMusic: "🎵 Musiqa",
    modeVoice: "🔊 Ovoz",
    placeholderText: "Xabar yozing…",
    placeholderImage: "Qanday rasm chizay? Masalan: yolg'iz archa, qor bosgan tog'…",
    placeholderVideo: "Video uchun tavsif yozing…",
    placeholderMusic: "Qanday musiqa yarataylik?",
    placeholderVoice: "Ovozga aylantirish uchun matn yozing…",
    pendingText: "Yozmoqda…",
    pendingImage: "Rasm yaratilmoqda…",
    pendingVideo: "Video yaratilmoqda (biroz uzoqroq davom etadi)…",
    pendingMusic: "Musiqa yaratilmoqda…",
    pendingVoice: "Ovoz yaratilmoqda…",
    pendingStyle: "Stil qo'llanmoqda…",
    coinUnit: "coin",
    newChatStartedMessage: "Yangi suhbat boshlandi! 👋 Nima haqida gaplashamiz?",
    genericError: "Xatolik",
    speechLang: "uz-UZ",
  },
  ru: {
    newChat: "Новый чат",
    navChat: "Чат",
    navGallery: "Готовые стили",
    navHelp: "Помощь",
    titleChat: "Чат",
    titleGallery: "Готовые стили",
    titleHelp: "Помощь",
    welcomeMessage: "Привет! 👋 Я MUBORAKXON. Выберите один из режимов ниже и напишите мне — создам текст, изображение, видео, музыку или голос.",
    galleryLead: "Выберите фото, нажмите на стиль — остальное сделаем мы.",
    helpTitle: "Как это работает",
    helpLineText: "💬 Текст — обычный разговор с MUBORAKXON.",
    helpLineImage: "🎨 Изображение — создаёт картинку по вашему описанию.",
    helpLineVideo: "🎬 Видео — создаёт короткое видео по описанию.",
    helpLineMusic: "🎵 Музыка — создаёт музыку по описанию.",
    helpLineVoice: "🔊 Голос — превращает ваш текст в голос.",
    helpLineStyles: "🖼 Готовые стили — применяет готовый стиль к вашему фото.",
    helpNote: "Каждое действие списывает монеты с баланса — цены смотрите в чипе баланса внизу.",
    formatLabel: "Формат",
    modelLabel: "Модель",
    videoModelWan: "🟢 Wan (дешевле)",
    videoModelKling: "🔵 Kling (качество)",
    modeText: "💬 Текст",
    modeImage: "🎨 Фото",
    modeVideo: "🎬 Видео",
    modeMusic: "🎵 Музыка",
    modeVoice: "🔊 Голос",
    placeholderText: "Напишите сообщение…",
    placeholderImage: "Какое изображение нарисовать? Например: одинокая ель, заснеженная гора…",
    placeholderVideo: "Опишите видео…",
    placeholderMusic: "Какую музыку создать?",
    placeholderVoice: "Напишите текст для озвучки…",
    pendingText: "Печатает…",
    pendingImage: "Создаём изображение…",
    pendingVideo: "Создаём видео (займёт чуть больше времени)…",
    pendingMusic: "Создаём музыку…",
    pendingVoice: "Создаём голос…",
    pendingStyle: "Применяем стиль…",
    coinUnit: "монет",
    newChatStartedMessage: "Начат новый разговор! 👋 О чём поговорим?",
    genericError: "Ошибка",
    speechLang: "ru-RU",
  },
  kk: {
    newChat: "Жаңа чат",
    navChat: "Чат",
    navGallery: "Дайын стильдер",
    navHelp: "Көмек",
    titleChat: "Чат",
    titleGallery: "Дайын стильдер",
    titleHelp: "Көмек",
    welcomeMessage: "Сәлем! 👋 Мен MUBORAKXON. Төмендегі режимдердің бірін таңдап, маған жазыңыз — мәтін, сурет, видео, музыка немесе дауыс жасаймын.",
    galleryLead: "Суретіңізді таңдаңыз, стильді басыңыз — қалғанын біз жасаймыз.",
    helpTitle: "Қалай жұмыс істейді",
    helpLineText: "💬 Мәтін — MUBORAKXON-мен әдеттегі сөйлесу.",
    helpLineImage: "🎨 Сурет — сипаттамаңыз бойынша сурет жасайды.",
    helpLineVideo: "🎬 Видео — сипаттамадан қысқа видео жасайды.",
    helpLineMusic: "🎵 Музыка — сипаттамадан музыка жасайды.",
    helpLineVoice: "🔊 Дауыс — мәтініңізді дауысқа айналдырады.",
    helpLineStyles: "🖼 Дайын стильдер — суретіңізге дайын стиль қолданады.",
    helpNote: "Әрбір әрекет балансыңыздан тиын алады — бағаларды төмендегі баланс чипінен көресіз.",
    formatLabel: "Формат",
    modelLabel: "Модель",
    videoModelWan: "🟢 Wan (арзан)",
    videoModelKling: "🔵 Kling (сапалы)",
    modeText: "💬 Мәтін",
    modeImage: "🎨 Сурет",
    modeVideo: "🎬 Видео",
    modeMusic: "🎵 Музыка",
    modeVoice: "🔊 Дауыс",
    placeholderText: "Хабар жазыңыз…",
    placeholderImage: "Қандай сурет салайын? Мысалы: жалғыз шырша, қар басқан тау…",
    placeholderVideo: "Видео үшін сипаттама жазыңыз…",
    placeholderMusic: "Қандай музыка жасайық?",
    placeholderVoice: "Дауысқа айналдыру үшін мәтін жазыңыз…",
    pendingText: "Жазуда…",
    pendingImage: "Сурет жасалуда…",
    pendingVideo: "Видео жасалуда (біраз уақыт алады)…",
    pendingMusic: "Музыка жасалуда…",
    pendingVoice: "Дауыс жасалуда…",
    pendingStyle: "Стиль қолданылуда…",
    coinUnit: "тиын",
    newChatStartedMessage: "Жаңа әңгіме басталды! 👋 Не туралы сөйлесеміз?",
    genericError: "Қате",
    speechLang: "kk-KZ",
  },
  tg: {
    newChat: "Чати нав",
    navChat: "Чат",
    navGallery: "Услубҳои тайёр",
    navHelp: "Кӯмак",
    titleChat: "Чат",
    titleGallery: "Услубҳои тайёр",
    titleHelp: "Кӯмак",
    welcomeMessage: "Салом! 👋 Ман MUBORAKXON. Яке аз режимҳои зеринро интихоб карда ба ман нависед — матн, расм, видео, мусиқӣ ё садо месозам.",
    galleryLead: "Суратро интихоб кунед, услубро пахш кунед — боқимондаро мо мекунем.",
    helpTitle: "Чӣ хел кор мекунад",
    helpLineText: "💬 Матн — сӯҳбати оддӣ бо MUBORAKXON.",
    helpLineImage: "🎨 Расм — тибқи тавсифи шумо расм месозад.",
    helpLineVideo: "🎬 Видео — аз тавсиф видеои кӯтоҳ месозад.",
    helpLineMusic: "🎵 Мусиқӣ — аз тавсиф мусиқӣ месозад.",
    helpLineVoice: "🔊 Садо — матни шуморо ба садо табдил медиҳад.",
    helpLineStyles: "🖼 Услубҳои тайёр — ба сурати шумо услуби тайёрро татбиқ мекунад.",
    helpNote: "Ҳар амал аз балансатон танга мегирад — нархҳоро дар чипи баланс дар поён мебинед.",
    formatLabel: "Формат",
    modelLabel: "Модел",
    videoModelWan: "🟢 Wan (арзон)",
    videoModelKling: "🔵 Kling (босифат)",
    modeText: "💬 Матн",
    modeImage: "🎨 Расм",
    modeVideo: "🎬 Видео",
    modeMusic: "🎵 Мусиқӣ",
    modeVoice: "🔊 Садо",
    placeholderText: "Паём нависед…",
    placeholderImage: "Чӣ хел расм кашам? Масалан: арчаи танҳо, кӯҳи барфпӯш…",
    placeholderVideo: "Барои видео тавсиф нависед…",
    placeholderMusic: "Чӣ хел мусиқӣ созем?",
    placeholderVoice: "Барои садо матн нависед…",
    pendingText: "Менависад…",
    pendingImage: "Расм сохта мешавад…",
    pendingVideo: "Видео сохта мешавад (андаке бештар вақт мегирад)…",
    pendingMusic: "Мусиқӣ сохта мешавад…",
    pendingVoice: "Садо сохта мешавад…",
    pendingStyle: "Услуб татбиқ мешавад…",
    coinUnit: "танга",
    newChatStartedMessage: "Сӯҳбати нав оғоз ёфт! 👋 Дар бораи чӣ гап занем?",
    genericError: "Хато",
    speechLang: "tg-TJ",
  },
  ky: {
    newChat: "Жаңы маек",
    navChat: "Маек",
    navGallery: "Даяр стилдер",
    navHelp: "Жардам",
    titleChat: "Маек",
    titleGallery: "Даяр стилдер",
    titleHelp: "Жардам",
    welcomeMessage: "Салам! 👋 Мен MUBORAKXON. Төмөнкү режимдердин бирин тандап, мага жазыңыз — текст, сүрөт, видео, музыка же үн түзөм.",
    galleryLead: "Сүрөтүңүздү тандаңыз, стилди басыңыз — калганын биз кылабыз.",
    helpTitle: "Кантип иштейт",
    helpLineText: "💬 Текст — MUBORAKXON менен жөнөкөй маек.",
    helpLineImage: "🎨 Сүрөт — сүрөттөмөңүз боюнча сүрөт түзөт.",
    helpLineVideo: "🎬 Видео — сүрөттөмөдөн кыска видео түзөт.",
    helpLineMusic: "🎵 Музыка — сүрөттөмөдөн музыка түзөт.",
    helpLineVoice: "🔊 Үн — текстиңизди үнгө айландырат.",
    helpLineStyles: "🖼 Даяр стилдер — сүрөтүңүзгө даяр стилди колдонот.",
    helpNote: "Ар бир аракет балансыңыздан монета алат — баалар төмөндөгү баланс чибинде көрсөтүлөт.",
    formatLabel: "Формат",
    modelLabel: "Модель",
    videoModelWan: "🟢 Wan (арзан)",
    videoModelKling: "🔵 Kling (сапаттуу)",
    modeText: "💬 Текст",
    modeImage: "🎨 Сүрөт",
    modeVideo: "🎬 Видео",
    modeMusic: "🎵 Музыка",
    modeVoice: "🔊 Үн",
    placeholderText: "Билдирүү жазыңыз…",
    placeholderImage: "Кандай сүрөт тартайын? Мисалы: жалгыз карагай, кар баскан тоо…",
    placeholderVideo: "Видео үчүн сүрөттөмө жазыңыз…",
    placeholderMusic: "Кандай музыка түзөлү?",
    placeholderVoice: "Үнгө айландыруу үчүн текст жазыңыз…",
    pendingText: "Жазууда…",
    pendingImage: "Сүрөт түзүлүүдө…",
    pendingVideo: "Видео түзүлүүдө (бир аз көбүрөөк убакыт алат)…",
    pendingMusic: "Музыка түзүлүүдө…",
    pendingVoice: "Үн түзүлүүдө…",
    pendingStyle: "Стил колдонулууда…",
    coinUnit: "монета",
    newChatStartedMessage: "Жаңы маек башталды! 👋 Эмне жөнүндө сүйлөшөбүз?",
    genericError: "Ката",
    speechLang: "ky-KG",
  },
  en: {
    newChat: "New chat",
    navChat: "Chat",
    navGallery: "Ready styles",
    navHelp: "Help",
    titleChat: "Chat",
    titleGallery: "Ready styles",
    titleHelp: "Help",
    welcomeMessage: "Hi! 👋 I'm MUBORAKXON. Pick one of the modes below and write to me — I'll generate text, an image, a video, music, or voice.",
    galleryLead: "Pick your photo, tap a style — we'll handle the rest.",
    helpTitle: "How it works",
    helpLineText: "💬 Text — a normal chat with MUBORAKXON.",
    helpLineImage: "🎨 Image — generates a picture from your description.",
    helpLineVideo: "🎬 Video — generates a short video from a description.",
    helpLineMusic: "🎵 Music — generates music from a description.",
    helpLineVoice: "🔊 Voice — converts your text into speech.",
    helpLineStyles: "🖼 Ready styles — applies a ready-made style to your photo.",
    helpNote: "Every action deducts coins from your balance — check prices in the balance chip below.",
    formatLabel: "Format",
    modelLabel: "Model",
    videoModelWan: "🟢 Wan (cheaper)",
    videoModelKling: "🔵 Kling (higher quality)",
    modeText: "💬 Text",
    modeImage: "🎨 Image",
    modeVideo: "🎬 Video",
    modeMusic: "🎵 Music",
    modeVoice: "🔊 Voice",
    placeholderText: "Type a message…",
    placeholderImage: "What should I draw? E.g.: a lone pine tree, a snowy mountain…",
    placeholderVideo: "Describe the video…",
    placeholderMusic: "What kind of music should we make?",
    placeholderVoice: "Type the text to convert to speech…",
    pendingText: "Typing…",
    pendingImage: "Generating image…",
    pendingVideo: "Generating video (this takes a bit longer)…",
    pendingMusic: "Generating music…",
    pendingVoice: "Generating voice…",
    pendingStyle: "Applying style…",
    coinUnit: "coins",
    newChatStartedMessage: "New conversation started! 👋 What shall we talk about?",
    genericError: "Error",
    speechLang: "en-US",
  },
};

let currentLang = "uz";

function tr(key) {
  const dict = MINIAPP_I18N[currentLang] || MINIAPP_I18N.uz;
  return dict[key] !== undefined ? dict[key] : MINIAPP_I18N.uz[key];
}

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

const newChatLabel = document.getElementById("newChatLabel");
const navChatLabel = document.getElementById("navChatLabel");
const navGalleryLabel = document.getElementById("navGalleryLabel");
const navHelpLabel = document.getElementById("navHelpLabel");
const welcomeBubbleText = document.getElementById("welcomeBubbleText");
const galleryLead = document.getElementById("galleryLead");
const helpTitle = document.getElementById("helpTitle");
const helpLineText = document.getElementById("helpLineText");
const helpLineImage = document.getElementById("helpLineImage");
const helpLineVideo = document.getElementById("helpLineVideo");
const helpLineMusic = document.getElementById("helpLineMusic");
const helpLineVoice = document.getElementById("helpLineVoice");
const helpLineStyles = document.getElementById("helpLineStyles");
const helpNote = document.getElementById("helpNote");
const formatLabel = document.getElementById("formatLabel");
const modelLabel = document.getElementById("modelLabel");
const videoModelWanBtn = document.getElementById("videoModelWanBtn");
const videoModelKlingBtn = document.getElementById("videoModelKlingBtn");
const modeTextBtn = document.getElementById("modeTextBtn");
const modeImageBtn = document.getElementById("modeImageBtn");
const modeVideoBtn = document.getElementById("modeVideoBtn");
const modeMusicBtn = document.getElementById("modeMusicBtn");
const modeVoiceBtn = document.getElementById("modeVoiceBtn");
const coinUnitLabel = document.getElementById("coinUnitLabel");

// ============ STATE ============

let currentMode = "text";
let currentAspect = "1:1";
let currentVideoModel = "wan";
let selectedStyleId = null;
let selectedStyleLabel = "";

// ============ TARJIMALARNI QO'LLASH ============

function setHelpLine(el, text) {
  if (!el) return;
  const idx = text.indexOf(" — ");
  if (idx === -1) {
    el.textContent = text;
    return;
  }
  const label = text.slice(0, idx);
  const rest = text.slice(idx);
  el.innerHTML = `<strong>${label}</strong>${rest}`;
}

function applyTranslations() {
  if (newChatLabel) newChatLabel.textContent = tr("newChat");
  if (navChatLabel) navChatLabel.textContent = tr("navChat");
  if (navGalleryLabel) navGalleryLabel.textContent = tr("navGallery");
  if (navHelpLabel) navHelpLabel.textContent = tr("navHelp");

  if (welcomeBubbleText) welcomeBubbleText.textContent = tr("welcomeMessage");
  if (galleryLead) galleryLead.textContent = tr("galleryLead");

  if (helpTitle) helpTitle.textContent = tr("helpTitle");
  setHelpLine(helpLineText, tr("helpLineText"));
  setHelpLine(helpLineImage, tr("helpLineImage"));
  setHelpLine(helpLineVideo, tr("helpLineVideo"));
  setHelpLine(helpLineMusic, tr("helpLineMusic"));
  setHelpLine(helpLineVoice, tr("helpLineVoice"));
  setHelpLine(helpLineStyles, tr("helpLineStyles"));
  if (helpNote) helpNote.textContent = tr("helpNote");

  if (formatLabel) formatLabel.textContent = tr("formatLabel");
  if (modelLabel) modelLabel.textContent = tr("modelLabel");
  if (videoModelWanBtn) videoModelWanBtn.textContent = tr("videoModelWan");
  if (videoModelKlingBtn) videoModelKlingBtn.textContent = tr("videoModelKling");

  if (modeTextBtn) modeTextBtn.textContent = tr("modeText");
  if (modeImageBtn) modeImageBtn.textContent = tr("modeImage");
  if (modeVideoBtn) modeVideoBtn.textContent = tr("modeVideo");
  if (modeMusicBtn) modeMusicBtn.textContent = tr("modeMusic");
  if (modeVoiceBtn) modeVoiceBtn.textContent = tr("modeVoice");

  if (coinUnitLabel) coinUnitLabel.textContent = tr("coinUnit");

  TITLES.chat = tr("titleChat");
  TITLES.gallery = tr("titleGallery");
  TITLES.help = tr("titleHelp");
  topbarTitle.textContent = TITLES[
    Object.keys(views).find((key) => views[key].classList.contains("active")) || "chat"
  ];

  if (recognition) {
    recognition.lang = tr("speechLang");
  }

  setMode(currentMode);
}

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

function placeholderFor(mode) {
  const map = {
    text: tr("placeholderText"),
    image: tr("placeholderImage"),
    video: tr("placeholderVideo"),
    music: tr("placeholderMusic"),
    voice: tr("placeholderVoice"),
  };
  return map[mode] || tr("placeholderText");
}

function setMode(mode) {
  currentMode = mode;

  document.querySelectorAll(".mode-chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.mode === mode);
  });

  imageSettingsRow.classList.toggle("hidden", mode !== "image");
  videoModelRow.classList.toggle("hidden", mode !== "video");

  messageInput.placeholder = placeholderFor(mode);
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
  wrapEl.querySelector(".bubble").textContent = "⚠️ " + (message || tr("genericError"));
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
      const pending = appendPendingBubble(tr("pendingText"));
      const form = new FormData();
      form.append("init_data", initData);
      form.append("message", text);
      const resp = await fetch("/api/chat", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || tr("genericError"));
      resolvePendingAsText(pending, data.reply);
      updateBalance(data.balance);

    } else if (currentMode === "image") {
      const pending = appendPendingBubble(tr("pendingImage"));
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      form.append("aspect_ratio", currentAspect);
      const resp = await fetch("/api/generate-image", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || tr("genericError"));
      resolvePendingAsImage(pending, data.image_url);
      updateBalance(data.balance);

    } else if (currentMode === "video") {
      const pending = appendPendingBubble(tr("pendingVideo"));
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      form.append("model_key", currentVideoModel);
      const resp = await fetch("/api/generate-video", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || tr("genericError"));
      resolvePendingAsVideo(pending, data.video_url);
      updateBalance(data.balance);

    } else if (currentMode === "music") {
      const pending = appendPendingBubble(tr("pendingMusic"));
      const form = new FormData();
      form.append("init_data", initData);
      form.append("prompt", text);
      const resp = await fetch("/api/generate-music", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || tr("genericError"));
      resolvePendingAsAudio(pending, data.audio_url);
      updateBalance(data.balance);

    } else if (currentMode === "voice") {
      const pending = appendPendingBubble(tr("pendingVoice"));
      const form = new FormData();
      form.append("init_data", initData);
      form.append("text", text);
      const resp = await fetch("/api/generate-voice", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || tr("genericError"));
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
      <div class="bubble">${tr("newChatStartedMessage")}</div>
    </div>
  `;
  switchView("chat");
});

// ============ MIKROFON (dikтация, mavjud bo'lsa) ============

const SpeechRecognitionCtor =
  window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;

if (SpeechRecognitionCtor) {
  micBtn.classList.remove("hidden");

  recognition = new SpeechRecognitionCtor();
  recognition.lang = tr("speechLang");
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
    const resp = await fetch("/api/styles?lang=" + encodeURIComponent(currentLang));
    const styles = await resp.json();

    stylesGrid.innerHTML = "";

    styles.forEach((style, index) => {
      const card = document.createElement("button");
      card.className = `style-card hue-${index % 6}`;
      card.type = "button";

      const emojiMatch = style.label.match(/\p{Emoji}/u);
      const emoji = emojiMatch ? emojiMatch[0] : "🎨";
      const text = style.label.replace(/\p{Emoji}/gu, "").trim();

      // MUHIM: agar bu stil uchun haqiqiy namuna rasm (thumbnail)
      // bo'lsa, emoji o'rniga o'sha rasm ko'rsatiladi — foydalanuvchi
      // stil natijasi qanday ko'rinishini oldindan ko'radi.
      const thumbInner = style.thumbnail
        ? `<img src="${style.thumbnail}" alt="${text}" loading="lazy" />`
        : emoji;

      card.innerHTML = `
        <div class="style-thumb">${thumbInner}</div>
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
  const pending = appendPendingBubble(tr("pendingStyle"));

  try {
    const form = new FormData();
    form.append("init_data", initData);
    form.append("style_id", selectedStyleId);
    form.append("photo", file);

    const resp = await fetch("/api/apply-style", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || tr("genericError"));

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

async function loadLang() {
  if (!initData) return "uz";

  try {
    const resp = await fetch("/api/lang?init_data=" + encodeURIComponent(initData));
    if (!resp.ok) throw new Error("lang so'rovi muvaffaqiyatsiz");
    const data = await resp.json();
    return data.lang && MINIAPP_I18N[data.lang] ? data.lang : "uz";
  } catch (e) {
    return "uz";
  }
}

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

async function init() {
  currentLang = await loadLang();
  applyTranslations();

  await Promise.all([loadStyles(), loadBalance()]);
}

init();
