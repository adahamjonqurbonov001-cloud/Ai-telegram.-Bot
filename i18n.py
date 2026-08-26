"""
Muborakxon bot uchun ko'p tillilik (i18n) moduli.
Qo'llab-quvvatlanadigan tillar: o'zbek, rus, qozoq, tojik, qirg'iz, ingliz.
"""

LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "kk": "🇰🇿 Қазақша",
    "tg": "🇹🇯 Тоҷикӣ",
    "ky": "🇰🇬 Кыргызча",
    "en": "🇬🇧 English",
}

DEFAULT_LANGUAGE = "uz"

TEXTS = {
    "choose_language": {
        "uz": "🌐 Tilni tanlang:",
        "ru": "🌐 Выберите язык:",
        "kk": "🌐 Тілді таңдаңыз:",
        "tg": "🌐 Забонро интихоб кунед:",
        "ky": "🌐 Тилди тандаңыз:",
        "en": "🌐 Choose your language:",
    },
    "language_set": {
        "uz": "✅ Til o'zbekchaga o'rnatildi.",
        "ru": "✅ Язык установлен на русский.",
        "kk": "✅ Тіл қазақ тіліне орнатылды.",
        "tg": "✅ Забон ба тоҷикӣ танзим шуд.",
        "ky": "✅ Тил кыргызчага коюлду.",
        "en": "✅ Language set to English.",
    },
    "btn_new_chat": {
        "uz": "🆕 Yangi chat", "ru": "🆕 Новый чат", "kk": "🆕 Жаңа чат",
        "tg": "🆕 Чати нав", "ky": "🆕 Жаңы маек", "en": "🆕 New chat",
    },
    "btn_styles": {
        "uz": "🖼 Tayyor stillar", "ru": "🖼 Готовые стили", "kk": "🖼 Дайын стильдер",
        "tg": "🖼 Услубҳои тайёр", "ky": "🖼 Даяр стилдер", "en": "🖼 Ready styles",
    },
    "btn_image": {
        "uz": "🎨 Rasm yaratish", "ru": "🎨 Создать изображение", "kk": "🎨 Сурет жасау",
        "tg": "🎨 Расм сохтан", "ky": "🎨 Сүрөт түзүү", "en": "🎨 Generate image",
    },
    "btn_video": {
        "uz": "🎬 Video yaratish", "ru": "🎬 Создать видео", "kk": "🎬 Видео жасау",
        "tg": "🎬 Видео сохтан", "ky": "🎬 Видео түзүү", "en": "🎬 Generate video",
    },
    "btn_voice": {
        "uz": "🔊 Matnni ovozga aylantirish", "ru": "🔊 Текст в голос",
        "kk": "🔊 Мәтінді дауысқа айналдыру", "tg": "🔊 Матнро ба садо табдил додан",
        "ky": "🔊 Текстти үнгө айландыруу", "en": "🔊 Text to speech",
    },
    "btn_music": {
        "uz": "🎵 Qo'shiq yaratish", "ru": "🎵 Создать песню", "kk": "🎵 Ән жасау",
        "tg": "🎵 Суруд сохтан", "ky": "🎵 Ыр түзүү", "en": "🎵 Generate song",
    },
    "btn_balance": {
        "uz": "💰 Balans", "ru": "💰 Баланс", "kk": "💰 Баланс",
        "tg": "💰 Баланс", "ky": "💰 Баланс", "en": "💰 Balance",
    },
    "btn_bonus": {
        "uz": "🎁 Kunlik bonus", "ru": "🎁 Ежедневный бонус", "kk": "🎁 Күнделікті бонус",
        "tg": "🎁 Бонуси ҳаррӯза", "ky": "🎁 Күндөлүк бонус", "en": "🎁 Daily bonus",
    },
    "btn_settings": {
        "uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки", "kk": "⚙️ Баптаулар",
        "tg": "⚙️ Танзимот", "ky": "⚙️ Жөндөөлөр", "en": "⚙️ Settings",
    },
    "btn_help": {
        "uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь", "kk": "ℹ️ Көмек",
        "tg": "ℹ️ Кӯмак", "ky": "ℹ️ Жардам", "en": "ℹ️ Help",
    },
    "btn_language": {
        "uz": "🌐 Til", "ru": "🌐 Язык", "kk": "🌐 Тіл",
        "tg": "🌐 Забон", "ky": "🌐 Тил", "en": "🌐 Language",
    },
    "welcome": {
        "uz": "Salom! 👋 Men *{bot_name}* — sun'iy intellekt asosida ishlaydigan botman.\n\n"
              "🪙 Sizga {start_balance} ta bepul coin berildi! Joriy balans: {balance}\n\n"
              "Quyidagi menyudan foydalaning:",
        "ru": "Привет! 👋 Я *{bot_name}* — бот на основе искусственного интеллекта.\n\n"
              "🪙 Вам начислено {start_balance} бесплатных монет! Текущий баланс: {balance}\n\n"
              "Используйте меню ниже:",
        "kk": "Сәлем! 👋 Мен *{bot_name}* — жасанды интеллект негізіндегі бот.\n\n"
              "🪙 Сізге {start_balance} тегін тиын берілді! Ағымдағы баланс: {balance}\n\n"
              "Төмендегі мәзірден пайдаланыңыз:",
        "tg": "Салом! 👋 Ман *{bot_name}* — боти асосёфта бар зеҳни сунъӣ.\n\n"
              "🪙 Ба шумо {start_balance} тангаи ройгон дода шуд! Бақияи ҷорӣ: {balance}\n\n"
              "Аз менюи зерин истифода баред:",
        "ky": "Салам! 👋 Мен *{bot_name}* — жасалма интеллект негизиндеги бот.\n\n"
              "🪙 Сизге {start_balance} акысыз монета берилди! Учурдагы баланс: {balance}\n\n"
              "Төмөнкү менюну колдонуңуз:",
        "en": "Hi! 👋 I'm *{bot_name}* — an AI-powered bot.\n\n"
              "🪙 You've received {start_balance} free coins! Current balance: {balance}\n\n"
              "Use the menu below:",
    },
    "insufficient_coins": {
        "uz": "❌ Coin yetarli emas. Kerak: {cost}, sizda: {balance}.",
        "ru": "❌ Недостаточно монет. Нужно: {cost}, у вас: {balance}.",
        "kk": "❌ Тиын жеткіліксіз. Керек: {cost}, сізде: {balance}.",
        "tg": "❌ Тангаҳо кофӣ нестанд. Лозим: {cost}, шумо доред: {balance}.",
        "ky": "❌ Монета жетишсиз. Керек: {cost}, сизде: {balance}.",
        "en": "❌ Not enough coins. Needed: {cost}, you have: {balance}.",
    },
    "bonus_claimed": {
        "uz": "🎁 Kunlik bonusingiz: +{amount} coin!\n💰 Joriy balans: {balance} coin",
        "ru": "🎁 Ваш ежедневный бонус: +{amount} монет!\n💰 Текущий баланс: {balance}",
        "kk": "🎁 Күнделікті бонусыңыз: +{amount} тиын!\n💰 Ағымдағы баланс: {balance}",
        "tg": "🎁 Бонуси ҳаррӯзаи шумо: +{amount} танга!\n💰 Бақияи ҷорӣ: {balance}",
        "ky": "🎁 Күндөлүк бонусуңуз: +{amount} монета!\n💰 Учурдагы баланс: {balance}",
        "en": "🎁 Your daily bonus: +{amount} coins!\n💰 Current balance: {balance}",
    },
    "bonus_already_claimed": {
        "uz": "⏳ Kunlik bonusni allaqachon olgansiz. Ertaga qayta urinib ko'ring!",
        "ru": "⏳ Вы уже получили сегодняшний бонус. Попробуйте завтра!",
        "kk": "⏳ Сіз бүгінгі бонусты алдыңыз. Ертең қайта көріңіз!",
        "tg": "⏳ Шумо аллакай бонуси имрӯзаро гирифтед. Пагоҳ бозоӣ кунед!",
        "ky": "⏳ Сиз бүгүнкү бонусту алгансыз. Эртең кайра аракет кылыңыз!",
        "en": "⏳ You've already claimed today's bonus. Try again tomorrow!",
    },
    "insufficient_coins": {
        "uz": "❌ Coin yetarli emas. Kerak: {cost}, sizda: {balance}.",
        "ru": "❌ Недостаточно монет. Нужно: {cost}, у вас: {balance}.",
        "kk": "❌ Тиын жеткіліксіз. Керек: {cost}, сізде: {balance}.",
        "tg": "❌ Тангаҳо кофӣ нестанд. Лозим: {cost}, шумо доред: {balance}.",
        "ky": "❌ Монета жетишсиз. Керек: {cost}, сизде: {balance}.",
        "en": "❌ Not enough coins. Needed: {cost}, you have: {balance}.",
    },
    "help_text": {
        "uz": "ℹ️ *Yordam*\n\n🆕 Yangi chat — suhbat tarixini tozalaydi\n"
              "🖼 Tayyor stillar — tayyor uslublardan birini tanlab, rasmingizni shu uslubda qayta ishlaydi (10 coin)\n"
              "🎨 Rasm yaratish — tavsif asosida rasm chizadi (10 coin)\n"
              "🎬 Video yaratish — tavsif asosida qisqa video yaratadi (30 coin)\n"
              "🔊 Matnni ovozga aylantirish — istalgan matnni ovozli xabarga aylantiradi (3 coin)\n"
              "🎵 Qo'shiq yaratish — mavzu asosida to'liq qo'shiq yaratadi (15 coin)\n"
              "💰 Balans — coin miqdoringizni ko'rsatadi\n⚙️ Sozlamalar — bot haqida ma'lumot\n\n"
              "Oddiy savolni yozsangiz, sun'iy intellekt sizga javob beradi (1 coin).",
        "ru": "ℹ️ *Помощь*\n\n🆕 Новый чат — очищает историю разговора\n"
              "🖼 Готовые стили — выберите стиль и обработайте своё фото (10 монет)\n"
              "🎨 Создать изображение — рисует по описанию (10 монет)\n"
              "🎬 Создать видео — создаёт короткое видео по описанию (30 монет)\n"
              "🔊 Текст в голос — превращает текст в голосовое сообщение (3 монеты)\n"
              "🎵 Создать песню — создаёт песню по теме (15 монет)\n"
              "💰 Баланс — показывает количество монет\n⚙️ Настройки — информация о боте\n\n"
              "Просто напишите вопрос — ИИ ответит вам (1 монета).",
        "kk": "ℹ️ *Көмек*\n\n🆕 Жаңа чат — әңгіме тарихын тазалайды\n"
              "🖼 Дайын стильдер — стильді таңдап, суретіңізді өңдейді (10 тиын)\n"
              "🎨 Сурет жасау — сипаттама бойынша сурет салады (10 тиын)\n"
              "🎬 Видео жасау — сипаттама бойынша қысқа видео жасайды (30 тиын)\n"
              "🔊 Мәтінді дауысқа айналдыру — мәтінді дауыстық хабарға айналдырады (3 тиын)\n"
              "🎵 Ән жасау — тақырып бойынша ән жасайды (15 тиын)\n"
              "💰 Баланс — тиын мөлшерін көрсетеді\n⚙️ Баптаулар — бот туралы ақпарат\n\n"
              "Жай ғана сұрақ жазыңыз — ЖИ сізге жауап береді (1 тиын).",
        "tg": "ℹ️ *Кӯмак*\n\n🆕 Чати нав — таърихи сӯҳбатро тоза мекунад\n"
              "🖼 Услубҳои тайёр — услубро интихоб карда, суратро коркард мекунад (10 танга)\n"
              "🎨 Расм сохтан — тибқи тавсиф расм мекашад (10 танга)\n"
              "🎬 Видео сохтан — тибқи тавсиф видеои кӯтоҳ месозад (30 танга)\n"
              "🔊 Матнро ба садо табдил додан — матнро ба паёми садоӣ табдил медиҳад (3 танга)\n"
              "🎵 Суруд сохтан — тибқи мавзӯъ суруд месозад (15 танга)\n"
              "💰 Баланс — миқдори тангаҳоро нишон медиҳад\n⚙️ Танзимот — маълумот дар бораи бот\n\n"
              "Танҳо саволатонро нависед — зеҳни сунъӣ ҷавоб медиҳад (1 танга).",
        "ky": "ℹ️ *Жардам*\n\n🆕 Жаңы маек — маек тарыхын тазалайт\n"
              "🖼 Даяр стилдер — стилди тандап, сүрөтүңүздү иштетет (10 монета)\n"
              "🎨 Сүрөт түзүү — сүрөттөмө боюнча сүрөт тартат (10 монета)\n"
              "🎬 Видео түзүү — сүрөттөмө боюнча кыска видео түзөт (30 монета)\n"
              "🔊 Текстти үнгө айландыруу — текстти үн билдирүүсүнө айландырат (3 монета)\n"
              "🎵 Ыр түзүү — тема боюнча ыр түзөт (15 монета)\n"
              "💰 Баланс — монета өлчөмүн көрсөтөт\n⚙️ Жөндөөлөр — бот жөнүндө маалымат\n\n"
              "Жөн гана суроо жазыңыз — ЖИ жооп берет (1 монета).",
        "en": "ℹ️ *Help*\n\n🆕 New chat — clears the conversation history\n"
              "🖼 Ready styles — pick a style and process your photo (10 coins)\n"
              "🎨 Generate image — draws based on your description (10 coins)\n"
              "🎬 Generate video — creates a short video based on your description (30 coins)\n"
              "🔊 Text to speech — turns text into a voice message (3 coins)\n"
              "🎵 Generate song — creates a song based on a topic (15 coins)\n"
              "💰 Balance — shows your coin balance\n⚙️ Settings — info about the bot\n\n"
              "Just type a question — the AI will answer you (1 coin).",
    },
    "settings_text": {
        "uz": "⚙️ *Sozlamalar*\n\nBot: `{bot_name}`\nMatn modeli: `{model}`\nRasm: `Higgsfield`\n"
              "Video modellari: Wan 2.6, Kling 1.6\nOvoz modeli: `{tts_model}`",
        "ru": "⚙️ *Настройки*\n\nБот: `{bot_name}`\nТекстовая модель: `{model}`\nИзображения: `Higgsfield`\n"
              "Видео модели: Wan 2.6, Kling 1.6\nГолосовая модель: `{tts_model}`",
        "kk": "⚙️ *Баптаулар*\n\nБот: `{bot_name}`\nМәтін моделі: `{model}`\nСурет: `Higgsfield`\n"
              "Видео модельдері: Wan 2.6, Kling 1.6\nДауыс моделі: `{tts_model}`",
        "tg": "⚙️ *Танзимот*\n\nБот: `{bot_name}`\nМодели матн: `{model}`\nРасм: `Higgsfield`\n"
              "Моделҳои видео: Wan 2.6, Kling 1.6\nМодели садо: `{tts_model}`",
        "ky": "⚙️ *Жөндөөлөр*\n\nБот: `{bot_name}`\nТекст модели: `{model}`\nСүрөт: `Higgsfield`\n"
              "Видео моделдери: Wan 2.6, Kling 1.6\nҮн модели: `{tts_model}`",
        "en": "⚙️ *Settings*\n\nBot: `{bot_name}`\nText model: `{model}`\nImage: `Higgsfield`\n"
              "Video models: Wan 2.6, Kling 1.6\nVoice model: `{tts_model}`",
    },
    "new_chat_started": {
        "uz": "🆕 Yangi suhbat boshlandi. Nima haqida gaplashamiz?",
        "ru": "🆕 Начат новый разговор. О чём поговорим?",
        "kk": "🆕 Жаңа әңгіме басталды. Не туралы сөйлесеміз?",
        "tg": "🆕 Сӯҳбати нав оғоз ёфт. Дар бораи чӣ гап занем?",
        "ky": "🆕 Жаңы маек башталды. Эмне жөнүндө сүйлөшөбүз?",
        "en": "🆕 New conversation started. What shall we talk about?",
    },
    "choose_style": {
        "uz": "🖼 Quyidagi stillardan birini tanlang:",
        "ru": "🖼 Выберите один из стилей:",
        "kk": "🖼 Төмендегі стильдердің бірін таңдаңыз:",
        "tg": "🖼 Яке аз услубҳои зеринро интихоб кунед:",
        "ky": "🖼 Төмөнкү стилдердин бирин тандаңыз:",
        "en": "🖼 Choose one of the styles below:",
    },
    "style_selected": {
        "uz": "✅ Tanlandi: {label}\n\n📸 Endi shu stilni qo'llash uchun rasmingizni yuboring.",
        "ru": "✅ Выбрано: {label}\n\n📸 Теперь отправьте фото, чтобы применить этот стиль.",
        "kk": "✅ Таңдалды: {label}\n\n📸 Енді осы стильді қолдану үшін суретіңізді жіберіңіз.",
        "tg": "✅ Интихоб шуд: {label}\n\n📸 Ҳоло барои татбиқи ин услуб суратро фиристед.",
        "ky": "✅ Тандалды: {label}\n\n📸 Эми ушул стилди колдонуу үчүн сүрөтүңүздү жөнөтүңүз.",
        "en": "✅ Selected: {label}\n\n📸 Now send your photo to apply this style.",
    },
    "style_applying": {
        "uz": "🎨 Stil qo'llanmoqda, biroz kuting...",
        "ru": "🎨 Применяем стиль, подождите...",
        "kk": "🎨 Стиль қолданылуда, күте тұрыңыз...",
        "tg": "🎨 Услуб татбиқ мешавад, лутфан интизор шавед...",
        "ky": "🎨 Стил колдонулууда, күтө туруңуз...",
        "en": "🎨 Applying style, please wait...",
    },
    "style_error": {
        "uz": "Kechirasiz, stil qo'llashda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при применении стиля произошла ошибка. Монеты не списаны. Попробуйте позже.",
        "kk": "Кешіріңіз, стильді қолдану кезінде қате орын алды. Тиын шегерілмеді. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми татбиқи услуб хато рӯй дод. Танга кам нашуд. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, стилди колдонууда ката кетти. Монета алынган жок. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while applying the style. Coins weren't deducted. Try again later.",
    },
    "hf_not_configured": {
        "uz": "⚠️ Higgsfield API kaliti sozlanmagan.",
        "ru": "⚠️ Ключ API Higgsfield не настроен.",
        "kk": "⚠️ Higgsfield API кілті орнатылмаған.",
        "tg": "⚠️ Калиди API Higgsfield танзим нашудааст.",
        "ky": "⚠️ Higgsfield API ачкычы жөндөлгөн эмес.",
        "en": "⚠️ Higgsfield API key is not configured.",
    },
    "image_prompt_ask": {
        "uz": "🎨 Qanday rasm chizishimni xohlaysiz? Tavsiflab yozing.\nMasalan: _qor bosgan tog' manzarasi, quyosh botishi_",
        "ru": "🎨 Какое изображение вы хотите? Опишите его.\nНапример: _заснеженные горы на закате_",
        "kk": "🎨 Қандай сурет салуымды қалайсыз? Сипаттап жазыңыз.\nМысалы: _қар басқан тау, күн батуы_",
        "tg": "🎨 Чӣ хел расм кашам? Тасвир кунед.\nМасалан: _кӯҳи барфпӯш, ғуруби офтоб_",
        "ky": "🎨 Кандай сүрөт тартышымды каалайсыз? Сүрөттөп жазыңыз.\nМисалы: _кар баскан тоо, күн батуусу_",
        "en": "🎨 What image would you like? Describe it.\nExample: _snowy mountains at sunset_",
    },
    "image_generating": {
        "uz": "🎨 Rasm yaratilmoqda, biroz kuting...",
        "ru": "🎨 Создаём изображение, подождите...",
        "kk": "🎨 Сурет жасалуда, күте тұрыңыз...",
        "tg": "🎨 Расм сохта мешавад, интизор шавед...",
        "ky": "🎨 Сүрөт түзүлүүдө, күтө туруңуз...",
        "en": "🎨 Generating image, please wait...",
    },
    "image_error": {
        "uz": "Kechirasiz, rasm yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при создании изображения произошла ошибка. Монеты не списаны. Попробуйте позже.",
        "kk": "Кешіріңіз, сурет жасау кезінде қате орын алды. Тиын шегерілмеді. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми сохтани расм хато рӯй дод. Танга кам нашуд. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, сүрөт түзүүдө ката кетти. Монета алынган жок. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while generating the image. Coins weren't deducted. Try again later.",
    },
    "video_choose_model": {
        "uz": "🎬 Qaysi model bilan video yaratamiz?\n\n🟢 Wan 2.6 — tezroq va arzonroq (~5 soniya)\n🔵 Kling 1.6 — sifatliroq (~10 soniya), biroz qimmatroq",
        "ru": "🎬 Какой моделью создать видео?\n\n🟢 Wan 2.6 — быстрее и дешевле (~5 сек)\n🔵 Kling 1.6 — качественнее (~10 сек), чуть дороже",
        "kk": "🎬 Қай модельмен видео жасаймыз?\n\n🟢 Wan 2.6 — жылдамырақ және арзанырақ (~5 сек)\n🔵 Kling 1.6 — сапалырақ (~10 сек), сәл қымбатырақ",
        "tg": "🎬 Бо кадом модел видео месозем?\n\n🟢 Wan 2.6 — тезтар ва арзонтар (~5 сония)\n🔵 Kling 1.6 — босифаттар (~10 сония), андаке қимматтар",
        "ky": "🎬 Кайсы модель менен видео түзөбүз?\n\n🟢 Wan 2.6 — тезирээк жана арзаныраак (~5 сек)\n🔵 Kling 1.6 — сапаттуураак (~10 сек), бир аз кымбатыраак",
        "en": "🎬 Which model should we use for the video?\n\n🟢 Wan 2.6 — faster and cheaper (~5 sec)\n🔵 Kling 1.6 — higher quality (~10 sec), slightly pricier",
    },
    "video_prompt_ask": {
        "uz": "✏️ Endi video uchun tavsif yozing.\nMasalan: _dengiz bo'yida quyosh botishi, to'lqinlar sohilga urilmoqda_",
        "ru": "✏️ Теперь опишите видео.\nНапример: _закат на берегу моря, волны бьются о берег_",
        "kk": "✏️ Енді видео үшін сипаттама жазыңыз.\nМысалы: _теңіз жағасында күн батуы, толқындар жағаға соғылуда_",
        "tg": "✏️ Ҳоло барои видео тавсиф нависед.\nМасалан: _ғуруби офтоб дар соҳили баҳр, мавҷҳо ба соҳил мезананд_",
        "ky": "✏️ Эми видео үчүн сүрөттөмө жазыңыз.\nМисалы: _деңиз боюндагы күн батуусу, толкундар жээкке урулууда_",
        "en": "✏️ Now describe the video.\nExample: _sunset by the sea, waves crashing on the shore_",
    },
    "video_generating": {
        "uz": "🎬 {label} orqali video yaratilmoqda...\nBu bir necha daqiqa vaqt olishi mumkin, iltimos kuting.",
        "ru": "🎬 Создаём видео через {label}...\nЭто может занять несколько минут, подождите.",
        "kk": "🎬 {label} арқылы видео жасалуда...\nБұл бірнеше минут алуы мүмкін, күте тұрыңыз.",
        "tg": "🎬 Тавассути {label} видео сохта мешавад...\nИн якчанд дақиқа вақт мегирад, интизор шавед.",
        "ky": "🎬 {label} аркылуу видео түзүлүүдө...\nБул бир нече мүнөт алышы мүмкүн, күтө туруңуз.",
        "en": "🎬 Generating video with {label}...\nThis may take a few minutes, please wait.",
    },
    "video_error": {
        "uz": "Kechirasiz, video yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при создании видео произошла ошибка. Монеты не списаны. Попробуйте позже.",
        "kk": "Кешіріңіз, видео жасау кезінде қате орын алды. Тиын шегерілмеді. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми сохтани видео хато рӯй дод. Танга кам нашуд. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, видео түзүүдө ката кетти. Монета алынган жок. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while generating the video. Coins weren't deducted. Try again later.",
    },
    "choose_button_below": {
        "uz": "Iltimos, pastdagi tugmalardan birini tanlang.",
        "ru": "Пожалуйста, выберите одну из кнопок ниже.",
        "kk": "Төмендегі түймелердің бірін таңдаңыз.",
        "tg": "Лутфан яке аз тугмаҳои зеринро интихоб кунед.",
        "ky": "Төмөнкү баскычтардын бирин тандаңыз.",
        "en": "Please choose one of the buttons below.",
    },
    "voice_ask_text": {
        "uz": "🔊 Qaysi matnni ovozga aylantirishim kerak? Matnni yozing.\nMasalan: _Assalomu alaykum, bugun ob-havo juda yaxshi_",
        "ru": "🔊 Какой текст озвучить? Напишите его.\nНапример: _Здравствуйте, сегодня отличная погода_",
        "kk": "🔊 Қандай мәтінді дауыстауым керек? Мәтінді жазыңыз.\nМысалы: _Ассалому алайкум, бүгін ауа райы өте жақсы_",
        "tg": "🔊 Кадом матнро ба садо табдил диҳам? Матнро нависед.\nМасалан: _Ассалому алайкум, имрӯз ҳаво хеле хуб аст_",
        "ky": "🔊 Кайсы текстти үнгө айландырышым керек? Текстти жазыңыз.\nМисалы: _Ассалому алейкум, бүгүн аба ырайы абдан жакшы_",
        "en": "🔊 What text should I convert to speech? Type it.\nExample: _Hello, the weather is great today_",
    },
    "voice_generating": {
        "uz": "🔊 Ovoz yaratilmoqda, biroz kuting...",
        "ru": "🔊 Создаём голос, подождите...",
        "kk": "🔊 Дауыс жасалуда, күте тұрыңыз...",
        "tg": "🔊 Садо сохта мешавад, интизор шавед...",
        "ky": "🔊 Үн түзүлүүдө, күтө туруңуз...",
        "en": "🔊 Generating voice, please wait...",
    },
    "voice_error": {
        "uz": "Kechirasiz, ovoz yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при создании голоса произошла ошибка. Монеты не списаны. Попробуйте позже.",
        "kk": "Кешіріңіз, дауыс жасау кезінде қате орын алды. Тиын шегерілмеді. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми сохтани садо хато рӯй дод. Танга кам нашуд. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, үн түзүүдө ката кетти. Монета алынган жок. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while generating the voice. Coins weren't deducted. Try again later.",
    },
    "music_ask_prompt": {
        "uz": "🎵 Qanday qo'shiq yarataylik? Mavzu, kayfiyat va janrni yozing.\nMasalan: _sevgi haqida quvnoq pop qo'shiq_",
        "ru": "🎵 Какую песню создать? Напишите тему, настроение и жанр.\nНапример: _весёлая поп-песня о любви_",
        "kk": "🎵 Қандай ән жасайық? Тақырып, көңіл-күй және жанрды жазыңыз.\nМысалы: _махаббат туралы көңілді поп ән_",
        "tg": "🎵 Чӣ хел суруд созем? Мавзӯъ, кайфият ва жанрро нависед.\nМасалан: _суруди шоду хурсандии попи ишқӣ_",
        "ky": "🎵 Кандай ыр түзөлү? Теманы, маанайды жана жанрды жазыңыз.\nМисалы: _сүйүү жөнүндө шайыр поп ыр_",
        "en": "🎵 What song should we create? Write the topic, mood, and genre.\nExample: _upbeat pop song about love_",
    },
    "music_generating": {
        "uz": "🎵 Qo'shiq yaratilmoqda, bu bir necha daqiqa vaqt olishi mumkin...",
        "ru": "🎵 Создаём песню, это может занять несколько минут...",
        "kk": "🎵 Ән жасалуда, бұл бірнеше минут алуы мүмкін...",
        "tg": "🎵 Суруд сохта мешавад, ин якчанд дақиқа вақт мегирад...",
        "ky": "🎵 Ыр түзүлүүдө, бул бир нече мүнөт алышы мүмкүн...",
        "en": "🎵 Generating song, this may take a few minutes...",
    },
    "music_error": {
        "uz": "Kechirasiz, qo'shiq yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при создании песни произошла ошибка. Монеты не списаны. Попробуйте позже.",
        "kk": "Кешіріңіз, ән жасау кезінде қате орын алды. Тиын шегерілмеді. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми сохтани суруд хато рӯй дод. Танга кам нашуд. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, ыр түзүүдө ката кетти. Монета алынган жок. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while generating the song. Coins weren't deducted. Try again later.",
    },
    "text_error": {
        "uz": "Kechirasiz, javob berishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
        "ru": "Извините, при ответе произошла ошибка. Попробуйте позже.",
        "kk": "Кешіріңіз, жауап беру кезінде қате орын алды. Кейінірек қайталап көріңіз.",
        "tg": "Мебахшед, ҳангоми ҷавоб додан хато рӯй дод. Баъдтар бозоӣ кунед.",
        "ky": "Кечиресиз, жооп берүүдө ката кетти. Кийинчерээк кайра аракет кылыңыз.",
        "en": "Sorry, an error occurred while responding. Please try again later.",
    },
    "video_model_wan": {
        "uz": "🟢 Wan 2.6 (arzon)", "ru": "🟢 Wan 2.6 (дешевле)", "kk": "🟢 Wan 2.6 (арзан)",
        "tg": "🟢 Wan 2.6 (арзон)", "ky": "🟢 Wan 2.6 (арзан)", "en": "🟢 Wan 2.6 (cheaper)",
    },
    "video_model_kling": {
        "uz": "🔵 Kling 1.6 (sifatli)", "ru": "🔵 Kling 1.6 (качество)", "kk": "🔵 Kling 1.6 (сапалы)",
        "tg": "🔵 Kling 1.6 (босифат)", "ky": "🔵 Kling 1.6 (сапаттуу)", "en": "🔵 Kling 1.6 (high quality)",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Berilgan til va kalit uchun tarjima matnini qaytaradi."""
    lang = lang if lang in LANGUAGES else DEFAULT_LANGUAGE
    template = TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get(DEFAULT_LANGUAGE, key)
    if kwargs:
        return template.format(**kwargs)
    return template
