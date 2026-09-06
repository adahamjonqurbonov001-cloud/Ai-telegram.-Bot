"""
MUBORAKXON — Sun'iy Intellekt Telegram Bot
- Matnli suhbat: Claude (Anthropic) API orqali
- Rasm yaratish: Higgsfield API orqali
- Rasmga stil berish: fal.ai FLUX image-to-image orqali
- Video yaratish: fal.ai orqali
- Matnni ovozga aylantirish: bepul edge-tts orqali
- Qo'shiq yaratish: fal.ai orqali
- Coin tizimi
- Admin statistikasi

O'rnatish:
    pip install -r requirements.txt

Ishga tushirish:
    python bot.py

Railway → Variables:
    TELEGRAM_BOT_TOKEN
    ANTHROPIC_API_KEY
    FAL_KEY
    HF_API_KEY_ID
    HF_API_KEY_SECRET
    ADMIN_ID
    PAYMENT_CARD_NUMBER
    PAYMENT_CARD_OWNER
    ADMIN_USERNAME
    COIN_PRICE_SOM
    COIN_PRICE_RUB
"""

import os
import io
import json
import asyncio
import logging

import httpx
import fal_client
import edge_tts

from i18n import t, LANGUAGES, DEFAULT_LANGUAGE

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from anthropic import Anthropic


# ============================================================
# SOZLAMALAR
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "BU_YERGA_TELEGRAM_TOKENINGIZNI_YOZING",
)

ANTHROPIC_API_KEY = os.environ.get(
    "ANTHROPIC_API_KEY",
    "BU_YERGA_ANTHROPIC_API_KEYINGIZNI_YOZING",
)

FAL_KEY = os.environ.get(
    "FAL_KEY",
    "BU_YERGA_FAL_API_KEYINGIZNI_YOZING",
)

HF_API_KEY_ID = os.environ.get(
    "HF_API_KEY_ID",
    "",
)

HF_API_KEY_SECRET = os.environ.get(
    "HF_API_KEY_SECRET",
    "",
)

ADMIN_ID = os.environ.get(
    "ADMIN_ID",
    "BU_YERGA_TELEGRAM_ID_INGIZNI_YOZING",
)

PAYMENT_CARD_NUMBER = os.environ.get(
    "PAYMENT_CARD_NUMBER",
    "8600 XXXX XXXX XXXX",
)

PAYMENT_CARD_OWNER = os.environ.get(
    "PAYMENT_CARD_OWNER",
    "F.I.SH.",
)

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "@sizning_username",
)

COIN_PRICE_SOM = int(
    os.environ.get(
        "COIN_PRICE_SOM",
        "400",
    )
)

COIN_PRICE_RUB = float(
    os.environ.get(
        "COIN_PRICE_RUB",
        "3",
    )
)

BOT_NAME = "MUBORAKXON"

WELCOME_IMAGE_PATH = "welcome.jpg"

MODEL_NAME = "claude-sonnet-4-6"

# edge-tts ovozi
TTS_VOICE = "uz-UZ-MadinaNeural"


# ============================================================
# MODELLAR
# ============================================================

HF_MODEL_ENDPOINT = (
    "https://api.higgsfield.ai/"
    "higgsfield-ai/soul/v2/standard"
)

VIDEO_MODELS = {
    "wan": {
        "label": "🟢 Wan 2.6 (arzon)",
        "model_id": "fal-ai/wan-t2v",
    },
    "kling": {
        "label": "🔵 Kling 1.6 (sifatli)",
        "model_id": (
            "fal-ai/kling-video/"
            "v1.6/standard/text-to-video"
        ),
    },
}

MUSIC_MODEL_ID = "fal-ai/minimax-music"


# ============================================================
# COIN NARXLARI
# ============================================================

COIN_START_BALANCE = 50

COIN_COST_TEXT = 1
COIN_COST_IMAGE = 10
COIN_COST_STYLE = 10
COIN_COST_VIDEO = 50
COIN_COST_VOICE = 3
COIN_COST_MUSIC = 15

DAILY_BONUS_AMOUNT = 10

COINS_FILE = "coins.json"
BONUS_FILE = "daily_bonus.json"
LANG_FILE = "user_languages.json"


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = (
    "Sen foydali, samimiy va bilimdon sun'iy intellekt "
    "yordamchisisan, isming Muborakxon. "
    "Foydalanuvchi bilan o'zbek tilida "
    "(agar u boshqa tilda yozmasa) muloqot qilasan. "
    "Javoblaring aniq, tushunarli va foydali bo'lsin."
)

MAX_HISTORY_MESSAGES = 20


# ============================================================
# LOGGER
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CLIENTLAR
# ============================================================

claude_client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)

os.environ["FAL_KEY"] = FAL_KEY


# ============================================================
# HOLATLAR
# ============================================================

conversation_history: dict[
    int,
    list[dict]
] = {}

awaiting_image_prompt: dict[
    int,
    bool
] = {}

awaiting_video_model_choice: dict[
    int,
    bool
] = {}

awaiting_video_prompt: dict[
    int,
    str
] = {}

awaiting_voice_text: dict[
    int,
    bool
] = {}

awaiting_music_prompt: dict[
    int,
    bool
] = {}

awaiting_style_photo: dict[
    int,
    str
] = {}


# ============================================================
# TIL FUNKSIYALARI
# ============================================================

def load_languages() -> dict:
    if os.path.exists(LANG_FILE):
        try:
            with open(
                LANG_FILE,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)
        except Exception:
            return {}

    return {}


def save_languages(data: dict):
    with open(
        LANG_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def get_lang(user_id: int) -> str:
    langs = load_languages()

    return langs.get(
        str(user_id),
        DEFAULT_LANGUAGE,
    )


def set_lang(
    user_id: int,
    lang: str,
):
    langs = load_languages()

    langs[str(user_id)] = lang

    save_languages(langs)


def language_inline_keyboard():
    buttons = []
    row = []

    for code, label in LANGUAGES.items():
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"lang:{code}",
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# ============================================================
# BONUS FUNKSIYALARI
# ============================================================

def load_bonus_data() -> dict:
    if os.path.exists(BONUS_FILE):
        try:
            with open(
                BONUS_FILE,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)
        except Exception:
            return {}

    return {}


def save_bonus_data(data: dict):
    with open(
        BONUS_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def can_claim_bonus(
    user_id: int,
) -> bool:
    import datetime

    data = load_bonus_data()

    last_claim = data.get(
        str(user_id)
    )

    if not last_claim:
        return True

    last_date = datetime.date.fromisoformat(
        last_claim
    )

    return last_date < datetime.date.today()


def mark_bonus_claimed(
    user_id: int,
):
    import datetime

    data = load_bonus_data()

    data[str(user_id)] = (
        datetime.date.today().isoformat()
    )

    save_bonus_data(data)


# ============================================================
# COIN TIZIMI
# ============================================================

def load_coins() -> dict:
    if os.path.exists(COINS_FILE):
        try:
            with open(
                COINS_FILE,
                "r",
                encoding="utf-8",
            ) as f:
                return json.load(f)
        except Exception:
            return {}

    return {}


def save_coins(data: dict):
    with open(
        COINS_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def get_balance(
    user_id: int,
) -> int:
    coins = load_coins()

    uid = str(user_id)

    if uid not in coins:
        coins[uid] = COIN_START_BALANCE
        save_coins(coins)

    return int(coins[uid])


def change_balance(
    user_id: int,
    amount: int,
) -> int:
    coins = load_coins()

    uid = str(user_id)

    if uid not in coins:
        coins[uid] = COIN_START_BALANCE

    coins[uid] += amount

    if coins[uid] < 0:
        coins[uid] = 0

    save_coins(coins)

    return int(coins[uid])


def is_admin(
    user_id: int,
) -> bool:
    return str(user_id) == str(ADMIN_ID)


# ============================================================
# MENYU
# ============================================================

def main_menu_keyboard(
    lang: str = DEFAULT_LANGUAGE,
):
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    t(lang, "btn_new_chat")
                ),
                KeyboardButton(
                    t(lang, "btn_styles")
                ),
            ],
            [
                KeyboardButton(
                    t(lang, "btn_image")
                ),
                KeyboardButton(
                    t(lang, "btn_video")
                ),
            ],
            [
                KeyboardButton(
                    t(lang, "btn_voice")
                ),
                KeyboardButton(
                    t(lang, "btn_music")
                ),
            ],
            [
                KeyboardButton(
                    t(lang, "btn_balance")
                ),
                KeyboardButton(
                    t(lang, "btn_bonus")
                ),
            ],
            [
                KeyboardButton(
                    t(lang, "btn_buy_coins")
                ),
                KeyboardButton(
                    t(lang, "btn_settings")
                ),
            ],
            [
                KeyboardButton(
                    t(lang, "btn_help")
                ),
                KeyboardButton(
                    t(lang, "btn_language")
                ),
            ],
        ],
        resize_keyboard=True,
    )


def video_model_keyboard(
    lang: str = DEFAULT_LANGUAGE,
):
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    t(
                        lang,
                        "video_model_wan",
                    )
                )
            ],
            [
                KeyboardButton(
                    t(
                        lang,
                        "video_model_kling",
                    )
                )
            ],
        ],
        resize_keyboard=True,
    )


# ============================================================
# TAYYOR STILLAR
# ============================================================

STYLE_TEMPLATES = {
    "bw_portrait": {
        "label": "🖤 Qora-oq portret",
        "prompt": (
            "Transform the provided photo into a "
            "dramatic black and white portrait, "
            "moody lighting, high contrast, "
            "cinematic shadows, professional "
            "studio photography. Preserve the "
            "person's identity and facial features."
        ),
    },

    "cinematic_car": {
        "label": "🚗 Kinematik avtomobil",
        "prompt": (
            "Transform the provided photo into "
            "cinematic automotive photography, "
            "dramatic lighting, film grain, "
            "wide angle, moody atmosphere, "
            "professional car advertisement style. "
            "Preserve the original car."
        ),
    },

    "vintage_sketch": {
        "label": "✏️ Vintage eskiz",
        "prompt": (
            "Transform the provided photo into a "
            "detailed vintage pencil sketch, "
            "cross-hatching shading, hand-drawn "
            "artistic illustration style. Preserve "
            "the original subject and composition."
        ),
    },

    "golden_hour": {
        "label": "🌅 Oltin soat portreti",
        "prompt": (
            "Transform the provided photo into a "
            "beautiful golden hour portrait, warm "
            "sunset lighting, soft bokeh background, "
            "natural cinematic photography. Preserve "
            "the person's identity and facial features."
        ),
    },

    "figurine": {
        "label": "🧸 Miniatura figurka",
        "prompt": (
            "Transform the provided subject into a "
            "hyper-realistic collectible figurine, "
            "detailed miniature toy style, product "
            "photography, studio lighting. Preserve "
            "recognizable features."
        ),
    },

    "fantasy_armor": {
        "label": "⚔️ Fentezi zirh",
        "prompt": (
            "Transform the provided portrait into an "
            "epic fantasy warrior wearing detailed "
            "medieval armor, cinematic fog, epic "
            "lighting, film still aesthetic. Preserve "
            "the person's identity and facial features."
        ),
    },
}


def styles_inline_keyboard():
    buttons = []
    row = []

    for key, info in STYLE_TEMPLATES.items():
        row.append(
            InlineKeyboardButton(
                info["label"],
                callback_data=f"style:{key}",
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# ============================================================
# HIGGSFIELD — RASM YARATISH
# ============================================================

async def generate_higgsfield_image(
    prompt: str,
) -> str | None:

    headers = {
        "Authorization": (
            f"Key "
            f"{HF_API_KEY_ID}:"
            f"{HF_API_KEY_SECRET}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "resolution": "720p",
    }

    async with httpx.AsyncClient(
        timeout=120
    ) as client:

        submit_resp = await client.post(
            HF_MODEL_ENDPOINT,
            headers=headers,
            json=payload,
        )

        submit_resp.raise_for_status()

        data = submit_resp.json()

        status_url = data.get(
            "status_url"
        )

        if not status_url:
            raise ValueError(
                "Higgsfield status_url qaytarmadi"
            )

        for _ in range(24):
            await asyncio.sleep(5)

            status_resp = await client.get(
                status_url,
                headers=headers,
            )

            status_resp.raise_for_status()

            status_data = status_resp.json()

            status = status_data.get(
                "status"
            )

            if status == "completed":
                results = (
                    status_data.get("images")
                    or status_data.get("results")
                    or []
                )

                if results:
                    return results[0].get(
                        "url"
                    )

                return None

            if status in (
                "failed",
                "nsfw",
                "cancelled",
            ):
                return None

    return None


# ============================================================
# TELEGRAM RASMINI YUKLAB OLISH
# ============================================================

async def download_telegram_image(
    image_url: str,
) -> bytes:

    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        resp = await client.get(
            image_url
        )

        resp.raise_for_status()

        return resp.content


# ============================================================
# FAL.AI — RASMGA STIL BERISH
# ============================================================

async def apply_fal_ai_style(
    image_bytes: bytes,
    style_prompt: str,
) -> str | None:
    """
    Telegram rasmini fal.ai CDN'iga yuklaydi
    va FLUX image-to-image orqali stil beradi.

    Model:
        fal-ai/flux/dev/image-to-image

    Parametrlar:
        strength = 0.65
        image_size = square_hd
    """

    def run_generation():

        image_url = fal_client.upload(
            image_bytes,
            "image.jpg",
        )

        result = fal_client.subscribe(
            "fal-ai/flux/dev/image-to-image",
            arguments={
                "image_url": image_url,
                "prompt": style_prompt,
                "strength": 0.65,
                "image_size": "square_hd",
            },
        )

        if not isinstance(
            result,
            dict,
        ):
            return None

        images = result.get(
            "images"
        ) or []

        if not images:
            return None

        first_image = images[0]

        if isinstance(
            first_image,
            dict,
        ):
            return first_image.get(
                "url"
            )

        return None

    return await asyncio.to_thread(
        run_generation
    )


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    conversation_history[chat_id] = []

    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False

    awaiting_video_prompt.pop(
        chat_id,
        None,
    )

    awaiting_voice_text[chat_id] = False
    awaiting_music_prompt[chat_id] = False
    awaiting_style_photo.pop(
        chat_id,
        None,
    )

    langs = load_languages()

    if str(chat_id) not in langs:

        await update.message.reply_text(
            t(
                DEFAULT_LANGUAGE,
                "choose_language",
            ),
            reply_markup=language_inline_keyboard(),
        )

        return

    await send_welcome(
        update,
        context,
        chat_id,
    )


async def send_welcome(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
):

    lang = get_lang(chat_id)

    balance = get_balance(chat_id)

    caption = t(
        lang,
        "welcome",
        bot_name=BOT_NAME,
        start_balance=COIN_START_BALANCE,
        balance=balance,
    )

    if os.path.exists(
        WELCOME_IMAGE_PATH
    ):

        with open(
            WELCOME_IMAGE_PATH,
            "rb",
        ) as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(
                    lang
                ),
            )

    else:

        await update.message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(
                lang
            ),
        )


# ============================================================
# TIL TANLASH
# ============================================================

async def language_selected_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id

    lang_code = query.data.split(
        ":",
        1,
    )[1]

    if lang_code not in LANGUAGES:
        return

    set_lang(
        chat_id,
        lang_code,
    )

    await query.message.reply_text(
        t(
            lang_code,
            "language_set",
        )
    )

    class _FakeUpdate:
        pass

    fake = _FakeUpdate()

    fake.message = query.message

    await send_welcome(
        fake,
        context,
        chat_id,
    )


# ============================================================
# ID
# ============================================================

async def show_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    await update.message.reply_text(
        f"🆔 Sizning Telegram ID'ingiz: "
        f"`{user_id}`",
        parse_mode="Markdown",
    )


# ============================================================
# BALANS
# ============================================================

async def show_balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    balance = get_balance(chat_id)

    await update.message.reply_text(
        f"💰 {balance} coin\n\n"
        f"💬 {COIN_COST_TEXT}  "
        f"🎨 {COIN_COST_IMAGE}  "
        f"🎬 {COIN_COST_VIDEO}  "
        f"🔊 {COIN_COST_VOICE}  "
        f"🎵 {COIN_COST_MUSIC}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# COIN SOTIB OLISH
# ============================================================

async def show_buy_coins(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    price_100_som = (
        COIN_PRICE_SOM * 100
    )

    await update.message.reply_text(
        t(
            lang,
            "buy_coins_info",
            price_som=COIN_PRICE_SOM,
            price_rub=COIN_PRICE_RUB,
            price_100_som=(
                f"{price_100_som:,}"
                .replace(",", " ")
            ),
            card_number=PAYMENT_CARD_NUMBER,
            card_owner=PAYMENT_CARD_OWNER,
            admin_username=ADMIN_USERNAME,
            user_id=chat_id,
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# ADMIN — COIN QO'SHISH
# ============================================================

async def add_coins_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await update.message.reply_text(
            "⛔ Bu buyruq faqat admin uchun."
        )

        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "❌ Foydalanish:\n\n"
            "/coin_qoshish <foydalanuvchi_id> "
            "<miqdor>\n\n"
            "Masalan:\n"
            "/coin_qoshish 123456789 100"
        )

        return

    try:

        target_id = int(
            context.args[0]
        )

        amount = int(
            context.args[1]
        )

    except (
        ValueError,
        TypeError,
    ):

        await update.message.reply_text(
            "❌ ID va miqdor raqam "
            "bo'lishi kerak.\n\n"
            "Masalan:\n"
            "/coin_qoshish 123456789 100"
        )

        return

    if amount == 0:

        await update.message.reply_text(
            "❌ Coin miqdori 0 "
            "bo'lishi mumkin emas."
        )

        return

    new_balance = change_balance(
        target_id,
        amount,
    )

    if amount > 0:

        action_text = (
            f"{amount} coin qo'shildi"
        )

    else:

        action_text = (
            f"{abs(amount)} coin ayirildi"
        )

    await update.message.reply_text(
        f"✅ Foydalanuvchi "
        f"{target_id} hisobida "
        f"{action_text}.\n\n"
        f"💰 Yangi balans: "
        f"{new_balance}"
    )

    try:

        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🎉 Hisobingiz o'zgartirildi!\n\n"
                f"🪙 O'zgarish: "
                f"{amount:+d} coin\n"
                f"💰 Yangi balans: "
                f"{new_balance}"
            ),
        )

    except Exception as e:

        logger.warning(
            "Foydalanuvchiga xabar "
            f"yuborib bo'lmadi: {e}"
        )


# ============================================================
# ADMIN — STATISTIKA
# ============================================================

async def show_stats_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    if not is_admin(user_id):

        await update.message.reply_text(
            "⛔ Bu buyruq faqat admin uchun."
        )

        return

    coins = load_coins()

    users_count = len(coins)

    total_coins = sum(
        int(balance)
        for balance in coins.values()
    )

    await update.message.reply_text(
        "📊 *BOT STATISTIKASI*\n\n"
        f"👥 Foydalanuvchilar: "
        f"*{users_count}*\n"
        f"🪙 Jami coin: "
        f"*{total_coins}*",
        parse_mode="Markdown",
    )


# ============================================================
# YORDAM
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    await update.message.reply_text(
        t(
            lang,
            "help_text",
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# SOZLAMALAR
# ============================================================

async def settings_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    await update.message.reply_text(
        t(
            lang,
            "settings_text",
            bot_name=BOT_NAME,
            model=MODEL_NAME,
            tts_model="edge-tts",
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# YANGI CHAT
# ============================================================

async def new_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    conversation_history[chat_id] = []

    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False

    awaiting_video_prompt.pop(
        chat_id,
        None,
    )

    awaiting_voice_text[chat_id] = False
    awaiting_music_prompt[chat_id] = False

    awaiting_style_photo.pop(
        chat_id,
        None,
    )

    lang = get_lang(chat_id)

    await update.message.reply_text(
        t(
            lang,
            "new_chat_started",
        ),
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# TAYYOR STILLAR MENYUSI
# ============================================================

async def show_styles_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_STYLE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_STYLE,
                balance=get_balance(
                    chat_id
                ),
            )
        )

        return

    await update.message.reply_text(
        t(
            lang,
            "choose_style",
        ),
        reply_markup=styles_inline_keyboard(),
    )


async def style_selected_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id

    lang = get_lang(chat_id)

    style_key = query.data.split(
        ":",
        1,
    )[1]

    if style_key not in STYLE_TEMPLATES:
        return

    awaiting_style_photo[
        chat_id
    ] = style_key

    style_label = STYLE_TEMPLATES[
        style_key
    ]["label"]

    await query.message.reply_text(
        t(
            lang,
            "style_selected",
            label=style_label,
        )
    )


# ============================================================
# TAYYOR STILLAR — RASM QABUL QILISH
# ============================================================

async def process_style_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    style_key = awaiting_style_photo.pop(
        chat_id,
        None,
    )

    if not style_key:
        return

    if get_balance(chat_id) < COIN_COST_STYLE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_STYLE,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    photo = update.message.photo[-1]

    tg_file = await context.bot.get_file(
        photo.file_id
    )

    image_url = (
        "https://api.telegram.org/file/bot"
        f"{TELEGRAM_BOT_TOKEN}/"
        f"{tg_file.file_path}"
    )

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="upload_photo",
    )

    await update.message.reply_text(
        t(
            lang,
            "style_applying",
        )
    )

    try:

        style_prompt = STYLE_TEMPLATES[
            style_key
        ]["prompt"]

        image_bytes = (
            await download_telegram_image(
                image_url
            )
        )

        result_url = (
            await apply_fal_ai_style(
                image_bytes,
                style_prompt,
            )
        )

        if not result_url:

            raise ValueError(
                "fal.ai rasm URL "
                "qaytarmadi"
            )

        new_balance = change_balance(
            chat_id,
            -COIN_COST_STYLE,
        )

        await update.message.reply_photo(
            photo=result_url,
            caption=(
                f"🖼 "
                f"{STYLE_TEMPLATES[style_key]['label']}\n\n"
                f"🪙 -{COIN_COST_STYLE} coin "
                f"({new_balance})"
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception as e:

        logger.error(
            "fal.ai stil qo'llash "
            f"xatosi: {e}"
        )

        await update.message.reply_text(
            t(
                lang,
                "style_error",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )


# ============================================================
# KUNLIK BONUS
# ============================================================

async def claim_daily_bonus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if not can_claim_bonus(chat_id):

        await update.message.reply_text(
            t(
                lang,
                "bonus_already_claimed",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    mark_bonus_claimed(chat_id)

    new_balance = change_balance(
        chat_id,
        DAILY_BONUS_AMOUNT,
    )

    await update.message.reply_text(
        t(
            lang,
            "bonus_claimed",
            amount=DAILY_BONUS_AMOUNT,
            balance=new_balance,
        ),
        reply_markup=main_menu_keyboard(
            lang
        ),
    )


# ============================================================
# RASM YARATISH
# ============================================================

async def ask_image_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_IMAGE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_IMAGE,
                balance=get_balance(
                    chat_id
                ),
            )
        )

        return

    awaiting_image_prompt[
        chat_id
    ] = True

    await update.message.reply_text(
        t(
            lang,
            "image_prompt_ask",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# VIDEO
# ============================================================

async def ask_video_model(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_VIDEO:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VIDEO,
                balance=get_balance(
                    chat_id
                ),
            )
        )

        return

    awaiting_video_model_choice[
        chat_id
    ] = True

    await update.message.reply_text(
        t(
            lang,
            "video_choose_model",
        ),
        reply_markup=video_model_keyboard(
            lang
        ),
    )


async def ask_video_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    model_key: str,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    awaiting_video_model_choice[
        chat_id
    ] = False

    awaiting_video_prompt[
        chat_id
    ] = model_key

    await update.message.reply_text(
        t(
            lang,
            "video_prompt_ask",
        ),
        parse_mode="Markdown",
    )


# ============================================================
# OVOZ — edge-tts
# ============================================================

async def ask_voice_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_VOICE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VOICE,
                balance=get_balance(
                    chat_id
                ),
            )
        )

        return

    awaiting_voice_text[
        chat_id
    ] = True

    await update.message.reply_text(
        t(
            lang,
            "voice_ask_text",
        ),
        parse_mode="Markdown",
    )


async def generate_voice_from_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_VOICE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VOICE,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="record_voice",
    )

    await update.message.reply_text(
        t(
            lang,
            "voice_generating",
        )
    )

    audio_path = (
        f"/tmp/voice_{chat_id}.mp3"
    )

    try:

        communicate = edge_tts.Communicate(
            text,
            TTS_VOICE,
        )

        await communicate.save(
            audio_path
        )

        if not os.path.exists(
            audio_path
        ):
            raise ValueError(
                "edge-tts audio fayl "
                "yaratmadi"
            )

        if os.path.getsize(
            audio_path
        ) == 0:
            raise ValueError(
                "edge-tts bo'sh audio "
                "fayl qaytardi"
            )

        new_balance = change_balance(
            chat_id,
            -COIN_COST_VOICE,
        )

        with open(
            audio_path,
            "rb",
        ) as audio_file:

            await update.message.reply_voice(
                voice=audio_file,
                caption=(
                    f"🔊 -{COIN_COST_VOICE} coin "
                    f"({new_balance})"
                ),
                reply_markup=main_menu_keyboard(
                    lang
                ),
            )

    except Exception as e:

        logger.error(
            f"edge-tts xatosi: {e}"
        )

        await update.message.reply_text(
            t(
                lang,
                "voice_error",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    finally:

        if os.path.exists(
            audio_path
        ):

            try:
                os.remove(
                    audio_path
                )
            except Exception:
                pass


# ============================================================
# QO'SHIQ
# ============================================================

async def ask_music_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_MUSIC:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_MUSIC,
                balance=get_balance(
                    chat_id
                ),
            )
        )

        return

    awaiting_music_prompt[
        chat_id
    ] = True

    await update.message.reply_text(
        t(
            lang,
            "music_ask_prompt",
        ),
        parse_mode="Markdown",
    )


async def generate_music_from_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_MUSIC:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_MUSIC,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="record_voice",
    )

    await update.message.reply_text(
        t(
            lang,
            "music_generating",
        )
    )

    try:

        def run_generation():

            return fal_client.subscribe(
                MUSIC_MODEL_ID,
                arguments={
                    "prompt": prompt
                },
            )

        result = await asyncio.to_thread(
            run_generation
        )

        audio_url = None

        if isinstance(
            result,
            dict,
        ):

            if (
                "audio" in result
                and isinstance(
                    result["audio"],
                    dict,
                )
            ):

                audio_url = result[
                    "audio"
                ].get("url")

            elif "audio_url" in result:

                audio_url = result[
                    "audio_url"
                ]

        if not audio_url:

            raise ValueError(
                "Audio URL topilmadi. "
                f"Natija: {result}"
            )

        new_balance = change_balance(
            chat_id,
            -COIN_COST_MUSIC,
        )

        await update.message.reply_audio(
            audio=audio_url,
            caption=(
                f"🎵 {prompt}\n\n"
                f"🪙 -{COIN_COST_MUSIC} coin "
                f"({new_balance})"
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception as e:

        logger.error(
            f"fal.ai qo'shiq yaratish "
            f"xatosi: {e}"
        )

        await update.message.reply_text(
            t(
                lang,
                "music_error",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )


# ============================================================
# VIDEO YARATISH
# ============================================================

async def generate_video_from_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    model_key: str,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_VIDEO:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VIDEO,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    model_info = VIDEO_MODELS[
        model_key
    ]

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="record_video",
    )

    await update.message.reply_text(
        t(
            lang,
            "video_generating",
            label=model_info[
                "label"
            ],
        ),
        reply_markup=main_menu_keyboard(
            lang
        ),
    )

    try:

        def run_generation():

            return fal_client.subscribe(
                model_info["model_id"],
                arguments={
                    "prompt": prompt
                },
            )

        result = await asyncio.to_thread(
            run_generation
        )

        video_url = None

        if isinstance(
            result,
            dict,
        ):

            if (
                "video" in result
                and isinstance(
                    result["video"],
                    dict,
                )
            ):

                video_url = result[
                    "video"
                ].get("url")

            elif "video_url" in result:

                video_url = result[
                    "video_url"
                ]

        if not video_url:

            raise ValueError(
                "Video URL topilmadi. "
                f"Natija: {result}"
            )

        new_balance = change_balance(
            chat_id,
            -COIN_COST_VIDEO,
        )

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action="upload_video",
        )

        await update.message.reply_video(
            video=video_url,
            caption=(
                f"🎬 {prompt}\n\n"
                f"🪙 -{COIN_COST_VIDEO} coin "
                f"({new_balance})"
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception as e:

        logger.error(
            f"fal.ai video yaratish "
            f"xatosi: {e}"
        )

        await update.message.reply_text(
            t(
                lang,
                "video_error",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )


# ============================================================
# HIGGSFIELD RASM YARATISH
# ============================================================

async def generate_image_from_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
):

    chat_id = update.effective_chat.id

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_IMAGE:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_IMAGE,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    if (
        not HF_API_KEY_ID
        or not HF_API_KEY_SECRET
    ):

        await update.message.reply_text(
            t(
                lang,
                "hf_not_configured",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="upload_photo",
    )

    await update.message.reply_text(
        t(
            lang,
            "image_generating",
        )
    )

    try:

        image_url = (
            await generate_higgsfield_image(
                prompt
            )
        )

        if not image_url:

            raise ValueError(
                "Higgsfield rasm URL "
                "qaytarmadi"
            )

        new_balance = change_balance(
            chat_id,
            -COIN_COST_IMAGE,
        )

        await update.message.reply_photo(
            photo=image_url,
            caption=(
                f"🖼 {prompt}\n\n"
                f"🪙 -{COIN_COST_IMAGE} coin "
                f"({new_balance})"
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception as e:

        logger.error(
            f"Higgsfield rasm yaratish "
            f"xatosi: {e}"
        )

        await update.message.reply_text(
            t(
                lang,
                "image_error",
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )


# ============================================================
# ASOSIY MESSAGE HANDLER
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat_id = update.effective_chat.id

    user_text = update.message.text

    lang = get_lang(chat_id)

    # --------------------------------------------------------
    # MENYU TUGMALARI
    # --------------------------------------------------------

    if user_text == t(
        lang,
        "btn_new_chat",
    ):

        await new_chat(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_styles",
    ):

        await show_styles_menu(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_image",
    ):

        await ask_image_prompt(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_video",
    ):

        await ask_video_model(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_voice",
    ):

        await ask_voice_text(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_music",
    ):

        await ask_music_prompt(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_balance",
    ):

        await show_balance(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_bonus",
    ):

        await claim_daily_bonus(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_buy_coins",
    ):

        await show_buy_coins(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_settings",
    ):

        await settings_command(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_help",
    ):

        await help_command(
            update,
            context,
        )

        return

    if user_text == t(
        lang,
        "btn_language",
    ):

        await update.message.reply_text(
            t(
                DEFAULT_LANGUAGE,
                "choose_language",
            ),
            reply_markup=language_inline_keyboard(),
        )

        return

    # --------------------------------------------------------
    # VIDEO MODEL TANLASH
    # --------------------------------------------------------

    if awaiting_video_model_choice.get(
        chat_id
    ):

        if user_text == t(
            lang,
            "video_model_wan",
        ):

            await ask_video_prompt(
                update,
                context,
                "wan",
            )

            return

        elif user_text == t(
            lang,
            "video_model_kling",
        ):

            await ask_video_prompt(
                update,
                context,
                "kling",
            )

            return

        else:

            await update.message.reply_text(
                t(
                    lang,
                    "choose_button_below",
                ),
                reply_markup=video_model_keyboard(
                    lang
                ),
            )

            return

    # --------------------------------------------------------
    # VIDEO PROMPT
    # --------------------------------------------------------

    if chat_id in awaiting_video_prompt:

        model_key = awaiting_video_prompt.pop(
            chat_id
        )

        await generate_video_from_prompt(
            update,
            context,
            user_text,
            model_key,
        )

        return

    # --------------------------------------------------------
    # IMAGE PROMPT
    # --------------------------------------------------------

    if awaiting_image_prompt.get(
        chat_id
    ):

        awaiting_image_prompt[
            chat_id
        ] = False

        await generate_image_from_prompt(
            update,
            context,
            user_text,
        )

        return

    # --------------------------------------------------------
    # VOICE TEXT
    # --------------------------------------------------------

    if awaiting_voice_text.get(
        chat_id
    ):

        awaiting_voice_text[
            chat_id
        ] = False

        await generate_voice_from_text(
            update,
            context,
            user_text,
        )

        return

    # --------------------------------------------------------
    # MUSIC PROMPT
    # --------------------------------------------------------

    if awaiting_music_prompt.get(
        chat_id
    ):

        awaiting_music_prompt[
            chat_id
        ] = False

        await generate_music_from_prompt(
            update,
            context,
            user_text,
        )

        return

    # --------------------------------------------------------
    # ODDIY CLAUDE CHAT
    # --------------------------------------------------------

    if get_balance(chat_id) < COIN_COST_TEXT:

        await update.message.reply_text(
            t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_TEXT,
                balance=get_balance(
                    chat_id
                ),
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    if chat_id not in conversation_history:

        conversation_history[
            chat_id
        ] = []

    history = conversation_history[
        chat_id
    ]

    history.append(
        {
            "role": "user",
            "content": user_text,
        }
    )

    if len(history) > MAX_HISTORY_MESSAGES:

        history = history[
            -MAX_HISTORY_MESSAGES:
        ]

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="typing",
    )

    lang_names = {
        "uz": "o'zbek",
        "ru": "русском",
        "kk": "қазақ",
        "tg": "тоҷикӣ",
        "ky": "кыргыз",
        "en": "English",
    }

    lang_name_for_prompt = lang_names.get(
        lang,
        "o'zbek",
    )

    dynamic_system_prompt = (
        SYSTEM_PROMPT
        + f" Javobingizni "
        f"{lang_name_for_prompt} "
        f"tilida yozing."
    )

    try:

        response = (
            claude_client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                system=dynamic_system_prompt,
                messages=history,
            )
        )

        reply_text = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

    except Exception as e:

        logger.error(
            f"Anthropic API xatosi: {e}"
        )

        reply_text = t(
            lang,
            "text_error",
        )

        conversation_history[
            chat_id
        ] = history

        await update.message.reply_text(
            reply_text,
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

        return

    history.append(
        {
            "role": "assistant",
            "content": reply_text,
        }
    )

    conversation_history[
        chat_id
    ] = history

    change_balance(
        chat_id,
        -COIN_COST_TEXT,
    )

    await update.message.reply_text(
        reply_text,
        reply_markup=main_menu_keyboard(
            get_lang(chat_id)
        ),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    missing = []

    if "BU_YERGA" in TELEGRAM_BOT_TOKEN:
        missing.append(
            "TELEGRAM_BOT_TOKEN"
        )

    if "BU_YERGA" in ANTHROPIC_API_KEY:
        missing.append(
            "ANTHROPIC_API_KEY"
        )

    if "BU_YERGA" in FAL_KEY:
        missing.append(
            "FAL_KEY"
        )

    if (
        not HF_API_KEY_ID
        or not HF_API_KEY_SECRET
    ):
        missing.append(
            "HF_API_KEY_ID / "
            "HF_API_KEY_SECRET"
        )

    if "BU_YERGA" in ADMIN_ID:
        missing.append(
            "ADMIN_ID"
        )

    if missing:

        print(
            "\n⚠️ DIQQAT: "
            "Quyidagi kalitlar "
            "sozlanmagan: "
            f"{', '.join(missing)}\n"
        )

        print(
            "Bot baribir ishga tushadi, "
            "lekin sozlanmagan "
            "funksiyalar ishlamaydi.\n"
        )

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMAND HANDLERS
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "clear",
            new_chat,
        )
    )

    app.add_handler(
        CommandHandler(
            "id",
            show_id,
        )
    )

    app.add_handler(
        CommandHandler(
            "balance",
            show_balance,
        )
    )

    app.add_handler(
        CommandHandler(
            "coin_qoshish",
            add_coins_admin,
        )
    )

    app.add_handler(
        CommandHandler(
            "statistika",
            show_stats_admin,
        )
    )

    # --------------------------------------------------------
    # CALLBACK HANDLERS
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            style_selected_callback,
            pattern=r"^style:",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            language_selected_callback,
            pattern=r"^lang:",
        )
    )

    # --------------------------------------------------------
    # PHOTO HANDLER
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            process_style_photo,
        )
    )

    # --------------------------------------------------------
    # TEXT HANDLER
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_message,
        )
    )

    print(
        f"🤖 {BOT_NAME} ishga tushdi..."
    )

    app.run_polling()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
