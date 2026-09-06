"""
MUBORAKXON — Sun'iy Intellekt Telegram Bot (tugmali menyu va coin tizimi bilan)
- Matnli suhbat: Claude (Anthropic) API orqali
- Rasm yaratish: Higgsfield API orqali
- Video yaratish: fal.ai orqali (Wan 2.6 yoki Kling 1.6)
- Matnni ovozga aylantirish: edge-tts (BEPUL, KALITSIZ)
- Tayyor stillar: fal.ai (Flux Image-to-Image) orqali
- Coin tizimi: har bir amal uchun coin yechiladi
- Admin buyruqlari: /coin_qoshish va /statistika
"""

import os
import io
import json
import logging
import asyncio

import httpx
import fal_client
import edge_tts  # Yangi bepul ovoz moduli
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

# === SOZLAMALAR ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "BU_YERGA_TELEGRAM_TOKENINGIZNI_YOZING")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "BU_YERGA_ANTHROPIC_API_KEYINGIZNI_YOZING")
FAL_KEY = os.environ.get("FAL_KEY", "BU_YERGA_FAL_API_KEYINGIZNI_YOZING")
HF_API_KEY_ID = os.environ.get("HF_API_KEY_ID", "")
HF_API_KEY_SECRET = os.environ.get("HF_API_KEY_SECRET", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "BU_YERGA_TELEGRAM_ID_INGIZNI_YOZING")
PAYMENT_CARD_NUMBER = os.environ.get("PAYMENT_CARD_NUMBER", "8600 XXXX XXXX XXXX")
PAYMENT_CARD_OWNER = os.environ.get("PAYMENT_CARD_OWNER", "F.I.SH.")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "@sizning_username")
COIN_PRICE_SOM = int(os.environ.get("COIN_PRICE_SOM", "400"))  # 1 coin narxi (so'mda)
COIN_PRICE_RUB = float(os.environ.get("COIN_PRICE_RUB", "3"))  # 1 coin narxi (rublda)

BOT_NAME = "MUBORAKXON"
WELCOME_IMAGE_PATH = "welcome.jpg"  # banner rasmini shu nom bilan loyihaga qo'ying

MODEL_NAME = "claude-sonnet-4-6"

# Higgsfield matndan rasm endpointi
HF_MODEL_ENDPOINT = "https://higgsfield.ai"

VIDEO_MODELS = {
    "wan": {"label": "🟢 Wan 2.6 (arzon)", "model_id": "fal-ai/wan-t2v"},
    "kling": {"label": "🔵 Kling 1.6 (sifatli)", "model_id": "fal-ai/kling-video/v1.6/standard/text-to-video"},
}

# fal.ai platformasidagi rasmga stil berish modeli
FAL_STYLE_MODEL = "fal-ai/flux/dev/image-to-image"
MUSIC_MODEL_ID = "fal-ai/minimax-music"

COIN_START_BALANCE = 50
COIN_COST_TEXT = 1
COIN_COST_IMAGE = 10
COIN_COST_STYLE = 10
COIN_COST_VIDEO = 50
COIN_COST_VOICE = 3
COIN_COST_MUSIC = 15
DAILY_BONUS_AMOUNT = 10
COINS_FILE = "coins.json"

SYSTEM_PROMPT = (
    "Sen foydali, samimiy va bilimdon sun'iy intellekt yordamchisisan, isming Muborakxon. "
    "Foydalanuvchi bilan o'zbek tilida (agar u boshqa tilda yozmasa) muloqot qilasan. "
    "Javoblaring aniq, tushunarli va foydali bo'lsin."
)

MAX_HISTORY_MESSAGES = 20

BTN_NEW_CHAT = "🆕 Yangi chat"
BTN_STYLES = "🖼 Tayyor stillar"
BTN_IMAGE = "🎨 Rasm yaratish"
BTN_VIDEO = "🎬 Video yaratish"
BTN_VOICE = "🔊 Matnni ovozga aylantirish"
BTN_MUSIC = "🎵 Qo'shiq yaratish"
BTN_BALANCE = "💰 Balans"
BTN_BONUS = "🎁 Kunlik bonus"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_HELP = "ℹ️ Yordam"
BTN_VIDEO_WAN = VIDEO_MODELS["wan"]["label"]
BTN_VIDEO_KLING = VIDEO_MODELS["kling"]["label"]

# === TAYYOR STILLAR (shablonlar) ===
STYLE_TEMPLATES = {
    "bw_portrait": {
        "label": "🖤 Qora-oq portret",
        "prompt": "dramatic black and white portrait photography, moody lighting, high contrast, cinematic shadows, professional studio look",
    },
    "cinematic_car": {
        "label": "🚗 Kinematik avtomobil",
        "prompt": "cinematic automotive photography, dramatic lighting, film grain, wide angle, moody atmosphere, professional car advertisement style",
    },
    "vintage_sketch": {
        "label": "✏️ Vintage eskiz",
        "prompt": "detailed pencil sketch portrait, vintage illustration style, cross-hatching shading, hand-drawn artistic look",
    },
    "golden_hour": {
        "label": "🌅 Oltin soat portreti",
        "prompt": "golden hour portrait photography, warm sunset lighting, soft bokeh background, natural cinematic look",
    },
    "figurine": {
        "label": "🧸 Miniatura figurka",
        "prompt": "hyper-realistic collectible figurine on a desk, product photography, detailed miniature toy style, studio lighting",
    },
    "fantasy_armor": {
        "label": "⚔️ Fentezi zirh",
        "prompt": "portrait wearing detailed fantasy medieval armor, cinematic fog, epic lighting, film still aesthetic",
    },
}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
os.environ["FAL_KEY"] = FAL_KEY

conversation_history: dict[int, list[dict]] = {}
awaiting_image_prompt: dict[int, bool] = {}
awaiting_video_model_choice: dict[int, bool] = {}
awaiting_video_prompt: dict[int, str] = {}
awaiting_voice_text: dict[int, bool] = {}
awaiting_music_prompt: dict[int, bool] = {}
awaiting_style_photo: dict[int, str] = {}  # chat_id -> style_key

BONUS_FILE = "daily_bonus.json"
LANG_FILE = "user_languages.json"


def load_languages() -> dict:
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_languages(data: dict):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_lang(user_id: int) -> str:
    langs = load_languages()
    return langs.get(str(user_id), DEFAULT_LANGUAGE)


def set_lang(user_id: int, lang: str):
    langs = load_languages()
    langs[str(user_id)] = lang
    save_languages(langs)


def language_inline_keyboard():
    buttons = []
    row = []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def load_bonus_data() -> dict:
    if os.path.exists(BONUS_FILE):
        try:
            with open(BONUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_bonus_data(data: dict):
    with open(BONUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def can_claim_bonus(user_id: int) -> bool:
    import datetime
    data = load_bonus_data()
    last_claim = data.get(str(user_id))
    if not last_claim:
        return True
    last_date = datetime.date.fromisoformat(last_claim)
    return last_date < datetime.date.today()


def mark_bonus_claimed(user_id: int):
    import datetime
    data = load_bonus_data()
    data[str(user_id)] = datetime.date.today().isoformat()
    save_bonus_data(data)


# === COIN TIZIMI ===

def load_coins() -> dict:
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_coins(data: dict):
    with open(COINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_balance(user_id: int) -> int:
    coins = load_coins()
    uid = str(user_id)
    if uid not in coins:
        coins[uid] = COIN_START_BALANCE
        save_coins(coins)
    return coins[uid]


def change_balance(user_id: int, amount: int) -> int:
    coins = load_coins()
    uid = str(user_id)
    if uid not in coins:
        coins[uid] = COIN_START_BALANCE
    coins[uid] += amount
    if coins[uid] < 0:
        coins[uid] = 0
    save_coins(coins)
    return coins[uid]


def is_admin(user_id: int) -> bool:
    return str(user_id) == str(ADMIN_ID)


# === MENYULAR ===

def main_menu_keyboard(lang: str = DEFAULT_LANGUAGE):
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t(lang, "btn_new_chat")), KeyboardButton(t(lang, "btn_styles"))],
            [KeyboardButton(t(lang, "btn_image")), KeyboardButton(t(lang, "btn_video"))],
            [KeyboardButton(t(lang, "btn_voice")), KeyboardButton(t(lang, "btn_music"))],
            [KeyboardButton(t(lang, "btn_balance")), KeyboardButton(t(lang, "btn_bonus"))],
            [KeyboardButton(t(lang, "btn_buy_coins")), KeyboardButton(t(lang, "btn_settings"))],
            [KeyboardButton(t(lang, "btn_help")), KeyboardButton(t(lang, "btn_language"))],
        ],
        resize_keyboard=True,
    )


def video_model_keyboard(lang: str = DEFAULT_LANGUAGE):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(t(lang, "video_model_wan"))], [KeyboardButton(t(lang, "video_model_kling"))]],
        resize_keyboard=True,
    )


# === HIGGSFIELD RASM GENERATSIYASI ===

async def generate_higgsfield_image(prompt: str) -> str | None:
    headers = {
        "Authorization": f"Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt, "aspect_ratio": "1:1", "resolution": "720p"}

    async with httpx.AsyncClient(timeout=120) as client:
        submit_resp = await client.post(HF_MODEL_ENDPOINT, headers=headers, json=payload)
        submit_resp.raise_for_status()
        data = submit_resp.json()
        status_url = data["status_url"]

        for _ in range(24):
            await asyncio.sleep(5)
            status_resp = await client.get(status_url, headers=headers)
            status_resp.raise_for_status()
            status_data = status_resp.json()
            status = status_data.get("status")

            if status == "completed":
                results = status_data.get("images") or status_data.get("results") or []
