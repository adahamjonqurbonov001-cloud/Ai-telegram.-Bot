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
    DATA_DIR  (ixtiyoriy — pastga qarang, "MUHIM: DATA SAQLASH" bo'limi)
"""

import os
import io
import json
import asyncio
import logging
import traceback
import base64
import re
import time

import httpx
import fal_client
import edge_tts
from PIL import Image

from i18n import t, LANGUAGES, DEFAULT_LANGUAGE, style_label

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

# edge-tts ovozlari — har bir interfeys tili uchun mos ovoz.
# edge-tts ovozlari — har bir interfeys tili uchun ayol VA erkak
# ovozi (MUHIM, YANGI). Avval har bir til uchun faqat bitta
# (ayol) ovoz qattiq bog'langan edi. Bu 4 ta yangi erkak ovoz
# (Sardor, Dmitry, Daulet, Guy) rasmiy Microsoft edge-tts
# ro'yxatida tasdiqlangan — xato chiqarmaydi. tg (tojik) va ky
# (qirg'iz) uchun na ayol, na erkak tabiiy ovoz yo'q — ikkalasi
# ham ruscha ovozga zaxiralangan (avvalgidek).
TTS_VOICE_MAP = {
    "uz": {"female": "uz-UZ-MadinaNeural", "male": "uz-UZ-SardorNeural"},
    "ru": {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"},
    "kk": {"female": "kk-KZ-AigulNeural", "male": "kk-KZ-DauletNeural"},
    "en": {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"},
    "tg": {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"},
    "ky": {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"},
}

DEFAULT_TTS_VOICE = "uz-UZ-MadinaNeural"


def get_tts_voice(lang: str, gender: str = "female") -> str:
    """
    Berilgan til va jins uchun mos edge-tts ovoz nomini
    qaytaradi. Noma'lum til yoki jins bo'lsa, standart (ayol,
    o'zbek) ovozga qaytadi — hech qachon xato bermaydi.
    """
    lang_voices = TTS_VOICE_MAP.get(lang, TTS_VOICE_MAP["uz"])
    return lang_voices.get(gender) or lang_voices.get("female") or DEFAULT_TTS_VOICE



# ============================================================
# MODELLAR
# ============================================================

HF_MODEL_ENDPOINT = (
    "https://api.higgsfield.ai/"
    "higgsfield-ai/soul/v2/standard"
)

# ------------------------------------------------------------
# VIDEO MODELLARI
# ------------------------------------------------------------
# MUHIM (Mini App yangilanishi): har bir model endi quyidagi
# qo'shimcha maydonlarga ega bo'ldi:
#
#   model_id        — matndan video (text-to-video) fal.ai
#                      endpointi
#   image_model_id   — rasmdan video (image-to-video) endpointi;
#                      model buni qo'llamasa — None
#   durations         — qo'llab-quvvatlanadigan davomiylik
#                      qiymatlari (soniyada, string); model
#                      buni qo'llamasa — None
#   aspect_ratios     — qo'llab-quvvatlanadigan format
#                      qiymatlari; model buni qo'llamasa — None
#
# Bu maydonlar Mini App'dagi tanlov menyusini (model / format /
# davomiylik / rasmdan video) to'g'ri chizish va fal.ai'ga
# FAQAT model qo'llaydigan parametrlarni yuborish uchun
# ishlatiladi (pastdagi generate_fal_video funksiyasiga qarang).
#
# Model ID'lar fal.ai'ning rasmiy hujjatlariga mos:
#   - "wan"        — eng arzon, lekin fal-ai/wan-t2v davomiylik/
#                     format parametrlarini qabul qilmaydi.
#   - "kling"       — fal-ai/kling-video/v1.6/standard —
#                     avvaldan ishlatilgan, o'zgarmadi.
#   - "kling_pro"   — fal-ai/kling-video/v2.6/pro — yangi,
#                     yuqori sifat + tabiiy audio, birroz
#                     qimmatroq (COIN_COST_VIDEO_PRO_EXTRA
#                     qo'shimcha narxiga qarang).
VIDEO_MODELS = {
    "wan": {
        "label": "🟢 Wan 2.6 (arzon)",
        "model_id": "fal-ai/wan-t2v",
        "image_model_id": None,
        "durations": None,
        "aspect_ratios": None,
    },
    "kling": {
        "label": "🔵 Kling 1.6 (sifatli)",
        "model_id": (
            "fal-ai/kling-video/"
            "v1.6/standard/text-to-video"
        ),
        "image_model_id": (
            "fal-ai/kling-video/"
            "v2.1/standard/image-to-video"
        ),
        "durations": ["5", "10"],
        "aspect_ratios": ["16:9", "9:16", "1:1"],
    },
    "kling_pro": {
        "label": "🟣 Kling 2.6 Pro (premium)",
        "model_id": (
            "fal-ai/kling-video/"
            "v2.6/pro/text-to-video"
        ),
        "image_model_id": (
            "fal-ai/kling-video/"
            "v2.1/pro/image-to-video"
        ),
        "durations": ["5", "10"],
        "aspect_ratios": ["16:9", "9:16", "1:1"],
    },
}

MUSIC_MODEL_ID = "fal-ai/minimax-music"

# fal.ai rasmga stil berish uchun model — Google Gemini 2.5
# Flash Image ("nano-banana").
STYLE_MODEL_ID = "fal-ai/gemini-25-flash-image/edit"

STYLE_QUALITY_SUFFIX = (
    "Ultra high resolution, extremely detailed, sharp focus, "
    "professional photographic quality, no blur, no compression "
    "artifacts, crisp fine details."
)


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

# Video Analyzer — video yuklab, undan professional video-
# generatsiya prompti yaratish (kadrlarni ffmpeg bilan ajratib,
# Claude'ning ko'rish (vision) qobiliyati orqali tahlil qilish).
COIN_COST_VIDEO_ANALYZE = 20

# "kling_pro" oddiy "kling"dan qimmatroq fal.ai narxiga ega
# (native audio + kengroq boshqaruv). Mini App shu qo'shimcha
# narxni COIN_COST_VIDEO ustiga qo'shadi. Telegram tarafidagi
# oddiy oqim o'zgarmaydi — u hali ham faqat wan/kling ishlatadi
# va oddiy COIN_COST_VIDEO'ni to'laydi.
COIN_COST_VIDEO_PRO_EXTRA = 30

# Rasmdan video (image-to-video) — bitta qo'shimcha kadr
# yuborilganda olinadigan ustama narx (matndan videoga nisbatan
# biroz qimmatroq hisoblash — fal.ai narxlari ham shunga yaqin).
COIN_COST_VIDEO_IMAGE_EXTRA = 10

DAILY_BONUS_AMOUNT = 10

# ------------------------------------------------------------
# MUHIM: DATA SAQLASH
# ------------------------------------------------------------
DATA_DIR = os.environ.get("DATA_DIR", ".")

if DATA_DIR != "." and not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

COINS_FILE = os.path.join(DATA_DIR, "coins.json")
BONUS_FILE = os.path.join(DATA_DIR, "daily_bonus.json")
LANG_FILE = os.path.join(DATA_DIR, "user_languages.json")


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

# Claude uchun til nomlari — "Javobingizni {lang_name} tilida
# yozing" ko'rsatmasida ishlatiladi. Bir nechta joyda (oddiy
# chat, agent yo'naltiruvchisi) qayta ishlatiladi.
LANG_NAMES = {
    "uz": "o'zbek",
    "ru": "русском",
    "kk": "қазақ",
    "tg": "тоҷикӣ",
    "ky": "кыргыз",
    "en": "English",
}


# ============================================================
# AGENT — MATNDAN AVTOMATIK TOOL TANLASH
# ============================================================
#
# MUHIM (YANGI): foydalanuvchi oddiy matn yozganda (rejim
# tanlamasdan), Claude endi shu matnni ko'rib, agar u aniq
# ravishda rasm/musiqa/ovoz so'rayotgan bo'lsa, MOS FUNKSIYANI
# O'ZI chaqiradi — foydalanuvchi qo'lda rejim almashtirishi
# shart emas. Bu Anthropic API'ning rasmiy "tool use" (function
# calling) imkoniyati orqali amalga oshiriladi — Claude
# tool_use qaytarsa, biz o'sha tool nomiga mos ravishda
# generate_fal_image/generate_fal_music/edge-tts funksiyalarini
# chaqiramiz (ular ALLAQACHON mavjud va sinovdan o'tgan).
#
# MUHIM: video ATAYLAB shu ro'yxatga kiritilmagan — video
# generatsiyasi bir necha daqiqa davom etadi va alohida
# job_id/polling infratuzilmasini talab qiladi (Mini App'da
# allaqachon shunday ishlaydi). Uni oddiy matn-javob oqimiga
# qo'shish "Failed to fetch" kabi muammolarni qaytarishi
# mumkin edi. Video uchun foydalanuvchi hamon "Video" rejimini
# tanlaydi.

AGENT_TOOLS = [
    {
        "name": "generate_image",
        "description": (
            "Generate an image from a text description. Use this "
            "tool ONLY when the user clearly and explicitly asks "
            "you to draw, create, or generate a picture, image, "
            "photo, or illustration — not when they merely mention "
            "an image in passing or ask a question about images in "
            "general."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "A vivid, detailed English description of "
                        "the image to generate."
                    ),
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "9:16", "16:9", "3:4", "4:3"],
                    "description": (
                        "Image aspect ratio. Use \"1:1\" if unclear."
                    ),
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_music",
        "description": (
            "Generate a short piece of music or song from a "
            "description. Use this tool ONLY when the user clearly "
            "and explicitly asks you to create, generate, or write "
            "a song or a piece of music."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Description of the music: genre, mood, "
                        "topic."
                    ),
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_voice",
        "description": (
            "Convert text to spoken audio. Use this tool ONLY when "
            "the user clearly and explicitly asks you to say "
            "something out loud, read text aloud, or convert text "
            "to speech/voice."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "The exact text to convert to speech, in "
                        "the same language the user used."
                    ),
                },
                "gender": {
                    "type": "string",
                    "enum": ["female", "male"],
                    "description": (
                        "Voice gender. Use \"female\" if unclear."
                    ),
                },
            },
            "required": ["text"],
        },
    },
]


async def classify_and_maybe_generate(
    chat_id: int,
    user_text: str,
    lang: str,
    history: list[dict],
) -> dict:
    """
    Claude'ga tool'lar bilan birga xabar yuboradi. Agar Claude
    rasm/musiqa/ovoz generatsiyasini tanlasa, mos funksiyani
    chaqirib natijani qaytaradi; aks holda oddiy matn javobini
    qaytaradi. Bitta joyda (bot.py) yozilgan — Telegram ham,
    Mini App ham shu funksiyani chaqiradi, ikkalasida ham bir
    xil xulq-atvor bo'lishi uchun.

    Qaytadigan lug'at shakllari:
        {"type": "text", "text": str, "cost": int}
        {"type": "image", "url": str, "cost": int, "prompt": str}
        {"type": "music", "url": str, "cost": int, "prompt": str}
        {"type": "voice", "audio_bytes": bytes, "cost": int, "text": str}
        {"type": "insufficient_coins", "cost": int}
        {"type": "error"}
    """

    lang_name = LANG_NAMES.get(lang, "o'zbek")

    dynamic_system_prompt = (
        SYSTEM_PROMPT
        + f" Javobingizni {lang_name} tilida yozing."
        + " If the user's message clearly and explicitly asks you "
        "to create an image, a piece of music, or spoken voice/"
        "audio, call the matching tool instead of replying with "
        "plain text. For anything else — including questions, "
        "requests for video, or ambiguous messages — just reply "
        "normally with text."
    )

    try:

        response = await asyncio.to_thread(
            claude_client.messages.create,
            model=MODEL_NAME,
            max_tokens=1024,
            system=dynamic_system_prompt,
            messages=history,
            tools=AGENT_TOOLS,
        )

    except Exception:

        logger.exception(
            "Agent (classify_and_maybe_generate) "
            "Claude chaqiruvi xatosi:"
        )

        return {"type": "error"}

    tool_use_block = next(
        (
            block
            for block in response.content
            if block.type == "tool_use"
        ),
        None,
    )

    if tool_use_block is None:

        reply_text = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

        return {
            "type": "text",
            "text": reply_text,
            "cost": COIN_COST_TEXT,
        }

    tool_name = tool_use_block.name
    tool_input = tool_use_block.input or {}

    if tool_name == "generate_image":

        cost = COIN_COST_IMAGE

        if get_balance(chat_id) < cost:
            return {
                "type": "insufficient_coins",
                "cost": cost,
            }

        prompt = tool_input.get(
            "prompt", user_text
        )

        aspect_ratio = tool_input.get(
            "aspect_ratio", "1:1"
        )

        image_url = await generate_fal_image(
            prompt,
            aspect_ratio=aspect_ratio,
        )

        if not image_url:
            return {"type": "error"}

        return {
            "type": "image",
            "url": image_url,
            "cost": cost,
            "prompt": prompt,
        }

    if tool_name == "generate_music":

        cost = COIN_COST_MUSIC

        if get_balance(chat_id) < cost:
            return {
                "type": "insufficient_coins",
                "cost": cost,
            }

        prompt = tool_input.get(
            "prompt", user_text
        )

        audio_url = await generate_fal_music(
            prompt
        )

        if not audio_url:
            return {"type": "error"}

        return {
            "type": "music",
            "url": audio_url,
            "cost": cost,
            "prompt": prompt,
        }

    if tool_name == "generate_voice":

        cost = COIN_COST_VOICE

        if get_balance(chat_id) < cost:
            return {
                "type": "insufficient_coins",
                "cost": cost,
            }

        text_to_speak = tool_input.get(
            "text", user_text
        )

        gender = tool_input.get(
            "gender", "female"
        )

        selected_voice = get_tts_voice(
            lang, gender
        )

        audio_path = (
            f"/tmp/agent_voice_{chat_id}_"
            f"{int(time.time())}.mp3"
        )

        try:

            communicate = edge_tts.Communicate(
                text_to_speak,
                selected_voice,
            )

            await communicate.save(
                audio_path
            )

            if (
                not os.path.exists(audio_path)
                or os.path.getsize(audio_path) == 0
            ):
                raise ValueError(
                    "edge-tts bo'sh audio "
                    "fayl qaytardi"
                )

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

        except Exception:

            logger.exception(
                "Agent ovoz generatsiyasi xatosi:"
            )

            return {"type": "error"}

        finally:

            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

        return {
            "type": "voice",
            "audio_bytes": audio_bytes,
            "cost": cost,
            "text": text_to_speak,
        }

    # Noma'lum tool nomi — amalda bo'lmasligi kerak, lekin
    # xavfsizlik uchun oddiy matn javobiga tushamiz.
    return {
        "type": "text",
        "text": t(lang, "text_error"),
        "cost": 0,
    }


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

# MUHIM (YANGI): foydalanuvchi "erkak" yoki "ayol" ovozini
# tanlaganidan keyin, matn kiritilguncha shu yerda saqlanadi.
voice_gender_choice: dict[
    int,
    str
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
# ADMIN'GA XATOLIK YUBORISH (DIAGNOSTIKA)
# ============================================================

async def notify_admin_error(
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
):
    if not ADMIN_ID or "BU_YERGA" in ADMIN_ID:
        return

    tb_text = traceback.format_exc()

    tb_text = re.sub(
        r"[A-Za-z0-9+/]{200,}={0,2}",
        "<<< base64 ma'lumot olib tashlandi >>>",
        tb_text,
    )

    if len(tb_text) > 3500:
        tb_text = "...\n" + tb_text[-3500:]

    try:

        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=(
                f"🔴 XATOLIK: {title}\n\n"
                f"{tb_text}"
            ),
        )

    except Exception as notify_exc:

        logger.warning(
            "Admin'ga xatolik xabarini "
            f"yuborib bo'lmadi: {notify_exc}"
        )


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


def escape_markdown_v1(text: str) -> str:

    if text is None:
        return ""

    for char in ("_", "*", "`", "["):
        text = text.replace(
            char,
            "\\" + char,
        )

    return text


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
        "prompt": (
            "Transform the provided photo into a "
            "dramatic black and white portrait, "
            "moody lighting, high contrast, "
            "cinematic shadows, professional "
            "studio photography. Preserve the "
            "person's identity and facial features."
        ),
        "thumbnail": "/thumbs/bw_portrait.jpg",
    },

    "cinematic_car": {
        "prompt": (
            "Transform the provided photo into "
            "cinematic automotive photography, "
            "dramatic lighting, film grain, "
            "wide angle, moody atmosphere, "
            "professional car advertisement style. "
            "Preserve the original car."
        ),
        "thumbnail": "/thumbs/cinematic_car.jpg",
    },

    "drift_racer": {
        "prompt": (
            "Transform the provided photo into a professional "
            "motorsport portrait: the person wearing a racing "
            "suit and holding a helmet, standing beside a "
            "modified sports car with dramatic tire smoke "
            "billowing in the background, motorsport event "
            "atmosphere with blurred banners and spectators, "
            "golden hour lighting, professional sports "
            "photography. Preserve the person's identity and "
            "facial features."
        ),
        "thumbnail": "/thumbs/drift_racer.jpg",
    },

    "grand_prix_driver": {
        "prompt": (
            "Transform the provided photo into a professional "
            "open-wheel racing driver portrait: the person "
            "wearing a modern racing suit covered in generic "
            "sponsor-style patches, seated confidently in a "
            "pit lane with a racing helmet resting on their "
            "knee, an open-wheel race car and pit garage "
            "blurred in the background, bright daylight, "
            "professional sports photography. Preserve the "
            "person's identity and facial features. Do not "
            "reproduce any real brand names or logos."
        ),
        "thumbnail": "/thumbs/grand_prix_driver.jpg",
    },

    "moody_studio_portrait": {
        "prompt": (
            "Transform the provided photo into a dramatic "
            "studio portrait: moody dark blue background, "
            "warm orange rim light tracing one side of the "
            "face and shoulder, three-quarter angled pose, "
            "shallow depth of field, high-end editorial "
            "photography style. Preserve the person's "
            "identity, facial features, and clothing."
        ),
        "thumbnail": "/thumbs/moody_studio_portrait.jpg",
    },

    "vintage_sketch": {
        "prompt": (
            "Transform the provided photo into an "
            "authentic 1980s retro photograph: warm "
            "faded film colors, soft grain, vintage "
            "clothing and styling typical of the era, "
            "a period-accurate background, analog "
            "photo quality. Preserve the person's "
            "identity and facial features."
        ),
        "thumbnail": "/thumbs/vintage_sketch.jpg",
    },

    "golden_hour": {
        "prompt": (
            "Transform the provided photo into a "
            "beautiful golden hour portrait, warm "
            "sunset lighting, soft bokeh background, "
            "natural cinematic photography. Preserve "
            "the person's identity and facial features."
        ),
    },

    "figurine": {
        "prompt": (
            "Transform the provided subject into a "
            "hyper-realistic collectible figurine, "
            "detailed miniature toy style, product "
            "photography, studio lighting. Preserve "
            "recognizable features."
        ),
        "thumbnail": "/thumbs/figurine.jpg",
    },

    "fantasy_armor": {
        "prompt": (
            "Transform the provided portrait into an "
            "epic fantasy warrior wearing detailed "
            "medieval armor, cinematic fog, epic "
            "lighting, film still aesthetic. Preserve "
            "the person's identity and facial features."
        ),
        "thumbnail": "/thumbs/fantasy_armor.jpg",
    },

    "mini_statue_desk": {
        "prompt": (
            "Transform the provided photo into a "
            "professional business portrait of the "
            "person sitting at a modern office desk, "
            "confidently holding a small collectible "
            "figurine/statuette that looks exactly like "
            "them in the palm of their hand. Sharp "
            "studio lighting, shallow depth of field, "
            "modern office background. Preserve the "
            "person's identity and facial features."
        ),
        "thumbnail": "/thumbs/mini_statue_desk.jpg",
    },

    "ink_portrait_color": {
        "prompt": (
            "Transform the provided photo into a "
            "detailed colored ink and pencil "
            "illustration portrait, fine crosshatching "
            "line work combined with selective color "
            "accents on clothing, hand-drawn editorial "
            "illustration style. Preserve the person's "
            "identity and facial features."
        ),
        "thumbnail": "/thumbs/ink_portrait_color.jpg",
    },

    "clone_multiply": {
        "prompt": (
            "Transform the provided photo into a "
            "surreal multiplicity composition showing "
            "five identical copies of the same person "
            "standing and sitting in different natural "
            "poses across an open plaza, cinematic "
            "overhead-angle photography, consistent "
            "lighting across all copies. Preserve the "
            "person's identity and facial features in "
            "every copy."
        ),
        "thumbnail": "/thumbs/clone_multiply.jpg",
    },

    "anime_portrait": {
        "prompt": (
            "Transform the provided photo into a "
            "vibrant anime-style illustration of the "
            "person, clean line art, cel-shaded "
            "coloring, dynamic outdoor cityscape "
            "background, expressive anime eyes while "
            "keeping a recognizable likeness. Preserve "
            "the person's identity and facial features."
        ),
        "thumbnail": "/thumbs/anime_portrait.jpg",
    },

    "cartoon_3d_portrait": {
        "prompt": (
            "Transform the provided photo into a "
            "colorful 3D animated movie character "
            "portrait, big expressive eyes, soft "
            "rounded friendly features, warm cinematic "
            "studio lighting, polished 3D animation "
            "render style. Preserve the person's "
            "identity and facial features."
        ),
        "thumbnail": "/thumbs/cartoon_3d_portrait.jpg",
    },

    "cinematic_workshop": {
        "prompt": (
            "Transform the provided photo into a "
            "cinematic moody portrait of the person "
            "sitting in a dim workshop or garage, warm "
            "backlighting streaming through dusty air, "
            "shallow depth of field with blurred tools "
            "and machinery in the background, dramatic "
            "film-still atmosphere. Preserve the "
            "person's identity and facial features."
        ),
        "thumbnail": "/thumbs/cinematic_workshop.jpg",
    },

    "steampunk_portrait": {
        "prompt": (
            "Transform the provided photo into an epic "
            "steampunk portrait: the person wearing "
            "brass goggles pushed up on the forehead, "
            "leather straps, brass gauges and mechanical "
            "armor pieces, standing before a sprawling "
            "industrial steampunk cityscape with giant "
            "gears, smokestacks, and airships in the sky, "
            "warm golden dramatic lighting. Preserve the "
            "person's identity and facial features."
        ),
        "thumbnail": "/thumbs/steampunk_portrait.jpg",
    },

    "paris_night_portrait": {
        "prompt": (
            "Transform the provided photo into an "
            "elegant evening portrait of the person "
            "wearing a stylish black blazer, leaning on "
            "a wrought-iron balcony railing, with the "
            "Eiffel Tower glowing at dusk in the "
            "background among classic Parisian buildings "
            "and a lit street lamp, cinematic travel "
            "photography style. Preserve the person's "
            "identity and facial features."
        ),
        "thumbnail": "/thumbs/paris_night_portrait.jpg",
    },

    "disco_night_portrait": {
        "prompt": (
            "Transform the provided photo into a "
            "vibrant portrait of the person at a retro "
            "disco nightclub, wearing a shiny patterned "
            "shirt with a gold chain necklace, colorful "
            "laser lights and a glowing neon sign in the "
            "background, energetic crowd dancing, film-"
            "photography aesthetic. Preserve the "
            "person's identity and facial features."
        ),
        "thumbnail": "/thumbs/disco_night_portrait.jpg",
    },
}


def styles_inline_keyboard(
    lang: str = DEFAULT_LANGUAGE,
):
    buttons = []
    row = []

    for key in STYLE_TEMPLATES.keys():
        row.append(
            InlineKeyboardButton(
                style_label(key, lang),
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

async def translate_prompt_to_english(
    text: str,
) -> str:

    try:

        response = await asyncio.to_thread(
            claude_client.messages.create,
            model=MODEL_NAME,
            max_tokens=200,
            system=(
                "You translate short image-generation "
                "prompts into natural, vivid English. "
                "Output ONLY the translated prompt text — "
                "no quotes, no explanation, no preamble. "
                "If the text is already in English, return "
                "it unchanged (lightly polished if useful)."
            ),
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ],
        )

        translated = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        ).strip()

        return translated or text

    except Exception as e:

        logger.warning(
            "Prompt tarjimasi muvaffaqiyatsiz, "
            f"asl matn ishlatiladi: {e}"
        )

        return text


IMAGE_MODEL_ID = "fal-ai/flux/dev"

FAL_ASPECT_TO_IMAGE_SIZE = {
    "1:1": "square_hd",
    "9:16": "portrait_16_9",
    "16:9": "landscape_16_9",
    "3:4": "portrait_4_3",
    "4:3": "landscape_4_3",
    "3:2": "landscape_4_3",
    "2:3": "portrait_4_3",
}


async def generate_fal_image(
    prompt: str,
    aspect_ratio: str = "1:1",
) -> str | None:

    english_prompt = await translate_prompt_to_english(
        prompt
    )

    image_size = FAL_ASPECT_TO_IMAGE_SIZE.get(
        aspect_ratio,
        "square_hd",
    )

    def run_generation():

        return fal_client.subscribe(
            IMAGE_MODEL_ID,
            arguments={
                "prompt": english_prompt,
                "image_size": image_size,
            },
        )

    result = await asyncio.to_thread(
        run_generation
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


async def generate_higgsfield_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "720p",
) -> str | None:

    english_prompt = await translate_prompt_to_english(
        prompt
    )

    headers = {
        "Authorization": (
            f"Key "
            f"{HF_API_KEY_ID}:"
            f"{HF_API_KEY_SECRET}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": english_prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
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


async def generate_fal_video(
    prompt: str,
    model_key: str,
    aspect_ratio: str | None = None,
    duration: str | None = None,
    image_bytes: bytes | None = None,
) -> str | None:
    """
    fal.ai orqali video yaratadi (qayta ishlatiladigan —
    Telegram handler ham, Mini App API ham shu funksiyani
    chaqiradi).

    MUHIM (Mini App yangilanishi): funksiya endi to'g'ridan-
    to'g'ri fal.ai model_id emas, balki VIDEO_MODELS lug'atidagi
    KALITNI (masalan "wan", "kling", "kling_pro") qabul qiladi —
    shunda har bir model qaysi qo'shimcha parametrlarni
    (aspect_ratio, duration) qo'llab-quvvatlashini o'zi hal
    qiladi va fal.ai'ga faqat mos parametrlarni yuboradi
    ("wan" masalan bularni umuman qabul qilmaydi).

    Agar image_bytes berilsa VA tanlangan model rasmdan video
    (image-to-video) endpointiga ega bo'lsa — rasm birinchi
    kadr sifatida ishlatiladi. Rasm hech qanday CDN'ga
    yuklanmasdan, apply_fal_ai_style funksiyasidagi kabi
    to'g'ridan-to'g'ri base64 "data URL" sifatida beriladi.
    """

    model_info = VIDEO_MODELS.get(model_key)

    if model_info is None:
        return None

    english_prompt = await translate_prompt_to_english(
        prompt
    )

    use_image = bool(
        image_bytes
        and model_info.get("image_model_id")
    )

    if use_image:

        target_model_id = model_info["image_model_id"]

        resized_image_bytes = resize_image_for_fal(
            image_bytes
        )

        base64_data = base64.b64encode(
            resized_image_bytes
        ).decode("ascii")

        arguments = {
            "prompt": english_prompt,
            "image_url": (
                f"data:image/jpeg;base64,{base64_data}"
            ),
        }

    else:

        target_model_id = model_info["model_id"]

        arguments = {
            "prompt": english_prompt,
        }

    allowed_durations = model_info.get("durations")

    if (
        duration
        and allowed_durations
        and duration in allowed_durations
    ):
        arguments["duration"] = duration

    allowed_aspect_ratios = model_info.get(
        "aspect_ratios"
    )

    if (
        aspect_ratio
        and allowed_aspect_ratios
        and aspect_ratio in allowed_aspect_ratios
    ):
        arguments["aspect_ratio"] = aspect_ratio

    def run_generation():

        return fal_client.subscribe(
            target_model_id,
            arguments=arguments,
        )

    result = await asyncio.to_thread(
        run_generation
    )

    if not isinstance(
        result,
        dict,
    ):
        return None

    if (
        "video" in result
        and isinstance(
            result["video"],
            dict,
        )
    ):
        return result["video"].get(
            "url"
        )

    if "video_url" in result:
        return result["video_url"]

    return None


async def generate_fal_music(
    prompt: str,
) -> str | None:

    english_prompt = await translate_prompt_to_english(
        prompt
    )

    def run_generation():

        return fal_client.subscribe(
            MUSIC_MODEL_ID,
            arguments={
                "prompt": english_prompt
            },
        )

    result = await asyncio.to_thread(
        run_generation
    )

    if not isinstance(
        result,
        dict,
    ):
        return None

    if (
        "audio" in result
        and isinstance(
            result["audio"],
            dict,
        )
    ):
        return result["audio"].get(
            "url"
        )

    if "audio_url" in result:
        return result["audio_url"]

    return None


# ============================================================
# RASMLARNI FAL.AI UCHUN KICHRAYTIRISH
# ============================================================
#
# MUHIM (YANGI): Mini App orqali yuklangan rasmlar (masalan
# telefon kamerasining to'liq o'lchamdagi surati) bir necha MB
# bo'lishi mumkin. base64'ga o'girilganda hajm ~33% oshadi, va
# fal.ai bunday katta "data:" URL'larni 10 MB dan oshsa rad
# etadi ("file_too_large" xatosi). Shu sabab har qanday rasm
# fal.ai'ga base64 sifatida yuborilishidan OLDIN shu funksiya
# orqali kichraytiriladi — natija sifatiga deyarli ta'sir
# qilmaydi (video/rasm modellari baribir bunchalik katta
# kirish o'lchamini talab qilmaydi).

def resize_image_for_fal(
    image_bytes: bytes,
    max_dimension: int = 1280,
    quality: int = 85,
) -> bytes:

    try:

        image = Image.open(
            io.BytesIO(image_bytes)
        )

        # RGBA/P kabi rejimlarni RGB'ga o'giramiz — aks holda
        # JPEG sifatida saqlashda xato chiqadi.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        width, height = image.size

        if max(width, height) > max_dimension:

            if width >= height:
                new_width = max_dimension
                new_height = int(
                    height * (max_dimension / width)
                )
            else:
                new_height = max_dimension
                new_width = int(
                    width * (max_dimension / height)
                )

            image = image.resize(
                (new_width, new_height),
                Image.LANCZOS,
            )

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
        )

        return output.getvalue()

    except Exception as e:

        # MUHIM: kichraytirish xato bersa ham (masalan buzuq
        # fayl), asl bayt oqimini qaytaramiz — funksiya
        # chaqiruvchi joyni butunlay to'xtatib qo'ymaydi. fal.ai
        # baribir o'z xatoligini qaytaradi, lekin bu kutilmagan
        # server xatosidan ko'ra ancha yaxshiroq holat.

        logger.warning(
            "Rasmni kichraytirib bo'lmadi, asl "
            f"fayl ishlatiladi: {e}"
        )

        return image_bytes


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

    def run_generation():

        resized_image_bytes = resize_image_for_fal(
            image_bytes
        )

        base64_data = base64.b64encode(
            resized_image_bytes
        ).decode("ascii")

        image_url = (
            f"data:image/jpeg;base64,{base64_data}"
        )

        result = fal_client.subscribe(
            STYLE_MODEL_ID,
            arguments={
                "image_urls": [image_url],
                "prompt": f"{style_prompt} {STYLE_QUALITY_SUFFIX}",
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


async def edit_image_with_instruction(
    image_bytes: bytes,
    instruction: str,
) -> str | None:
    """
    MUHIM (YANGI): "Tayyor stillar"dagi tayyor shablonlardan farqli
    o'laroq, foydalanuvchi o'z so'zlari bilan yozgan erkin
    buyruqqa ("bu rasmni tunga aylantir", "sochini qizil qil" va
    h.k.) qarab rasmni tahrirlaydi. Backend AYNAN bir xil —
    apply_fal_ai_style (fal-ai/gemini-25-flash-image/edit) — faqat
    tayyor "style_prompt" o'rniga foydalanuvchi buyrug'i (avval
    ingliz tiliga tarjima qilingan holda) beriladi.
    """

    english_instruction = await translate_prompt_to_english(
        instruction
    )

    return await apply_fal_ai_style(
        image_bytes,
        english_instruction,
    )


# ============================================================
# RASM BO'YICHA SAVOL-JAVOB / TAHRIRLASH (Claude vision)
# ============================================================
#
# MUHIM (YANGI): avval foydalanuvchi biror rasm yuborib, "bu
# rasmda nima bor?", "buni tasvirla" kabi erkin savol bersa,
# Claude'ga RASMNING O'ZI umuman yuborilmasdi — faqat matn
# (agar bo'lsa) alohida Claude chat so'roviga ketardi, shuning
# uchun Claude "men rasmlarni ko'ra olmayman" deb javob berardi
# (bu haqiqatan ham to'g'ri edi, chunki rasm hech qachon API
# so'roviga qo'shilmagan edi).
#
# Endi rasm baytlari to'g'ridan-to'g'ri Anthropic API'ning
# "image" content block'iga (base64, media_type bilan)
# qo'shiladi — bu Claude'ning rasmiy ko'rish (vision)
# imkoniyati, faqat promptga "sen ko'ra olasan" deb yozish
# bilan farqli o'laroq, RASM HAQIQATAN API so'roviga boradi.
#
# Shu bilan birga, Claude'ga "edit_image" tool'i ham beriladi —
# agar foydalanuvchi savol emas, balki TAHRIRLASH so'rasa
# ("buni qorong'i qil", "fonini o'zgartir"), Claude shu tool'ni
# chaqiradi va biz mavjud edit_image_with_instruction (fal.ai)
# funksiyasini ishga tushiramiz. Aks holda Claude rasmni ko'rib,
# oddiy MATN javobi beradi.

IMAGE_QA_TOOLS = [
    {
        "name": "edit_image",
        "description": (
            "Edit or transform the provided image. Use this tool "
            "ONLY when the user clearly asks you to change, edit, "
            "transform, or stylize the image itself — not when "
            "they ask a question about the image or ask you to "
            "describe/analyze it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": (
                        "A clear, detailed English instruction "
                        "describing exactly how to edit the image."
                    ),
                },
            },
            "required": ["instruction"],
        },
    },
]


def _guess_image_media_type(image_bytes: bytes) -> str:
    """
    Rasm baytlarining boshlanishiga (magic bytes) qarab
    media_type'ni aniqlaydi — Anthropic API buni JPEG/PNG/WebP
    uchun to'g'ri ko'rsatishni talab qiladi.
    """

    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"

    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"

    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"

    # Zaxira: Telegram/Mini App'dan kelgan rasmlar deyarli har
    # doim JPEG — noma'lum holatda shu bilan davom etamiz.
    return "image/jpeg"


async def analyze_or_edit_photo(
    image_bytes: bytes,
    user_text: str,
    lang: str,
) -> dict:
    """
    Rasmni Claude'ga (vision) yuboradi. Foydalanuvchi matni
    tahrirlash so'rovi bo'lsa, edit_image tool'i chaqiriladi va
    natija rasm sifatida qaytadi; aks holda Claude rasmni ko'rib,
    oddiy matn javobini qaytaradi.

    Qaytadi:
        {"type": "text", "text": str, "cost": int}
        {"type": "image", "url": str, "cost": int, "prompt": str}
        {"type": "error"}
    """

    lang_name = LANG_NAMES.get(lang, "o'zbek")

    media_type = _guess_image_media_type(image_bytes)

    base64_data = base64.b64encode(
        image_bytes
    ).decode("ascii")

    dynamic_system_prompt = (
        SYSTEM_PROMPT
        + f" Javobingizni {lang_name} tilida yozing."
        + " The user has sent you a photo. Look at it carefully "
        "and respond to their message about it. If they clearly "
        "ask you to edit or transform the image, use the "
        "edit_image tool. Otherwise, describe or answer their "
        "question about the image directly in plain text."
    )

    if not user_text:
        user_text = "Rasmda nima borligini tasvirlab bering."

    try:

        response = await asyncio.to_thread(
            claude_client.messages.create,
            model=MODEL_NAME,
            max_tokens=1024,
            system=dynamic_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": user_text,
                        },
                    ],
                }
            ],
            tools=IMAGE_QA_TOOLS,
        )

    except Exception:

        logger.exception(
            "analyze_or_edit_photo — Claude "
            "vision chaqiruvi xatosi:"
        )

        return {"type": "error"}

    tool_use_block = next(
        (
            block
            for block in response.content
            if block.type == "tool_use"
        ),
        None,
    )

    if tool_use_block is not None and tool_use_block.name == "edit_image":

        instruction = (
            tool_use_block.input or {}
        ).get("instruction", user_text)

        result_url = await apply_fal_ai_style(
            image_bytes,
            instruction,
        )

        if not result_url:
            return {"type": "error"}

        return {
            "type": "image",
            "url": result_url,
            "cost": COIN_COST_STYLE,
            "prompt": instruction,
        }

    reply_text = "".join(
        block.text
        for block in response.content
        if block.type == "text"
    ).strip()

    if not reply_text:
        return {"type": "error"}

    return {
        "type": "text",
        "text": reply_text,
        "cost": COIN_COST_TEXT,
    }


# ============================================================
# VIDEO ANALYZER — video'dan prompt yaratish
# ============================================================
#
# MUHIM (YANGI): foydalanuvchi video yuklaydi → ffmpeg orqali
# bir necha kadr (rasm) ajratiladi → shu kadrlar Claude'ning
# ko'rish (vision) qobiliyati orqali tahlil qilinadi → natijada
# tayyor video-generatsiya modellari (Kling/Wan) uchun
# optimallashtirilgan professional ingliz tilidagi prompt
# yaratiladi. Bu funksiya ham ffmpeg talab qiladi — video+ovoz
# funksiyasi bilan bir xil (nixpacks.toml orqali o'rnatiladi).

VIDEO_ANALYSIS_FRAME_COUNT = 5

VIDEO_ANALYZER_SYSTEM_PROMPT = (
    "You are a professional video analyst and prompt engineer for "
    "AI video generation models such as Kling and Wan. You will be "
    "shown several still frames sampled evenly across one short "
    "video, in chronological order. Analyze them carefully and "
    "respond in EXACTLY this format:\n\n"
    "SCENE: ...\n"
    "CAMERA: ...\n"
    "SUBJECT: ...\n"
    "ACTION: ...\n"
    "ENVIRONMENT: ...\n"
    "LIGHTING: ...\n"
    "COLORS: ...\n"
    "STYLE: ...\n"
    "MOTION: ...\n"
    "TIMING: ...\n"
    "IMPORTANT DETAILS: ...\n"
    "PROMPT: <a single, flowing, professional video-generation "
    "prompt in English that combines everything above into one "
    "paragraph, optimized for an AI video generator>\n\n"
    "Always write your entire response in English, regardless of "
    "what language the person might address you in."
)


async def extract_video_frames(
    video_bytes: bytes,
    job_id: str,
    frame_count: int = VIDEO_ANALYSIS_FRAME_COUNT,
) -> list[str]:
    """
    ffmpeg yordamida yuklangan videodan bir necha kadrni (teng
    oraliqlarda) rasm sifatida ajratib oladi va ularning fayl
    yo'llarini ro'yxat qilib qaytaradi.
    """

    tmp_dir = "/tmp/muborakxon_media"
    os.makedirs(tmp_dir, exist_ok=True)

    video_path = os.path.join(
        tmp_dir, f"analyze_src_{job_id}.mp4"
    )

    with open(video_path, "wb") as f:
        f.write(video_bytes)

    # Video davomiyligini ffprobe orqali bilib olamiz — agar
    # muvaffaqiyatsiz bo'lsa, taxminiy 5 soniyaga zaxiralanamiz
    # (baribir teng oraliqlarda urinib ko'radi).
    duration = 5.0

    try:

        probe = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        out_bytes, _ = await probe.communicate()

        duration = float(out_bytes.decode().strip())

    except Exception:

        logger.warning(
            "ffprobe davomiylikni bilib "
            "ololmadi, zaxira qiymat "
            "ishlatiladi"
        )

    frame_paths = []

    for i in range(frame_count):

        # Har bir kadrni intervalning O'RTASIDAN olamiz (chekka
        # nuqtalar ko'pincha qora/tiniq bo'lmaydi).
        timestamp = duration * (i + 0.5) / frame_count

        frame_path = os.path.join(
            tmp_dir, f"analyze_frame_{job_id}_{i}.jpg"
        )

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "3",
            frame_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await proc.communicate()

        if os.path.exists(frame_path):
            frame_paths.append(frame_path)

    try:
        os.remove(video_path)
    except Exception:
        pass

    return frame_paths


async def analyze_video_with_claude(
    frame_paths: list[str],
) -> tuple[str, str]:
    """
    Ajratilgan kadrlarni Claude'ga (vision) yuboradi va tahlil +
    video-generatsiya promptini qaytaradi:
        (tahlil_matni, generatsiya_prompti)
    """

    content_blocks = []

    for path in frame_paths:

        with open(path, "rb") as f:
            image_bytes = f.read()

        b64_data = base64.b64encode(
            image_bytes
        ).decode("ascii")

        content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_data,
                },
            }
        )

    content_blocks.append(
        {
            "type": "text",
            "text": (
                "These frames are sampled evenly across one "
                "short video, in chronological order. Analyze "
                "them as instructed."
            ),
        }
    )

    response = await asyncio.to_thread(
        claude_client.messages.create,
        model=MODEL_NAME,
        max_tokens=800,
        system=VIDEO_ANALYZER_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": content_blocks,
            }
        ],
    )

    full_text = "".join(
        block.text
        for block in response.content
        if block.type == "text"
    ).strip()

    if "PROMPT:" in full_text:

        analysis_part, prompt_part = full_text.split(
            "PROMPT:", 1
        )

        analysis_part = analysis_part.strip()
        prompt_part = prompt_part.strip()

    else:

        # Zaxira: format kutilganidek kelmasa ham, foydalanuvchi
        # hech bo'lmasa to'liq javobni ko'radi va uni video
        # promptiga o'zi moslashtirishi mumkin.
        analysis_part = full_text
        prompt_part = full_text

    for path in frame_paths:
        try:
            os.remove(path)
        except Exception:
            pass

    return analysis_part, prompt_part


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
    voice_gender_choice.pop(chat_id, None)
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

    try:

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
                card_number=escape_markdown_v1(
                    PAYMENT_CARD_NUMBER
                ),
                card_owner=escape_markdown_v1(
                    PAYMENT_CARD_OWNER
                ),
                admin_username=escape_markdown_v1(
                    ADMIN_USERNAME
                ),
                user_id=chat_id,
            ),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception as e:

        logger.error(
            f"show_buy_coins xatosi: {e}"
        )

        try:

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
                reply_markup=main_menu_keyboard(
                    lang
                ),
            )

        except Exception as e2:

            logger.error(
                "show_buy_coins zaxira "
                f"urinishi ham xato berdi: {e2}"
            )

            await update.message.reply_text(
                "❌ Xatolik yuz berdi. "
                "Iltimos, keyinroq urinib "
                "ko'ring yoki admin bilan "
                "bog'laning.",
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
    voice_gender_choice.pop(chat_id, None)
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
        reply_markup=styles_inline_keyboard(lang),
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

    label_text = style_label(
        style_key,
        lang,
    )

    await query.message.reply_text(
        t(
            lang,
            "style_selected",
            label=label_text,
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

        # MUHIM (YANGI): foydalanuvchi stil tanlamasdan, shunchaki
        # bir rasm yuborgan (masalan "bu rasmda nima bor?" degan
        # sarlavha bilan yoki sarlavhasiz). Avval bunday holatda
        # bot HECH NARSA qilmasdi. Endi rasm Claude'ga (vision)
        # yuboriladi — Claude uni ko'rib, savolga javob beradi
        # yoki (agar aniq tahrirlash so'ralgan bo'lsa) fal.ai
        # orqali tahrirlaydi.

        if get_balance(chat_id) < COIN_COST_STYLE:

            await update.message.reply_text(
                t(
                    lang,
                    "insufficient_coins",
                    cost=COIN_COST_STYLE,
                    balance=get_balance(chat_id),
                ),
                reply_markup=main_menu_keyboard(lang),
            )

            return

        photo = update.message.photo[-1]

        tg_file = await context.bot.get_file(
            photo.file_id
        )

        if tg_file.file_path.startswith("http"):
            image_url = tg_file.file_path
        else:
            image_url = (
                "https://api.telegram.org/file/bot"
                f"{TELEGRAM_BOT_TOKEN}/"
                f"{tg_file.file_path}"
            )

        await context.bot.send_chat_action(
            chat_id=chat_id,
            action="typing",
        )

        try:

            image_bytes = await download_telegram_image(
                image_url
            )

        except Exception:

            logger.exception(
                "Rasm tahlili — yuklab olishda xatolik:"
            )

            await notify_admin_error(
                context,
                "Rasm tahlili — yuklab olish",
            )

            await update.message.reply_text(
                t(lang, "image_edit_error"),
                reply_markup=main_menu_keyboard(lang),
            )

            return

        caption_text = update.message.caption or ""

        result = await analyze_or_edit_photo(
            image_bytes,
            caption_text,
            lang,
        )

        if result["type"] == "error":

            await notify_admin_error(
                context,
                "Rasm tahlili/tahrirlash",
            )

            await update.message.reply_text(
                t(lang, "image_edit_error"),
                reply_markup=main_menu_keyboard(lang),
            )

            return

        if result["type"] == "text":

            change_balance(
                chat_id,
                -result["cost"],
            )

            await update.message.reply_text(
                result["text"],
                reply_markup=main_menu_keyboard(lang),
            )

            return

        if result["type"] == "image":

            new_balance = change_balance(
                chat_id,
                -result["cost"],
            )

            await update.message.reply_photo(
                photo=result["url"],
                caption=(
                    f"🖼 {result['prompt']}\n\n"
                    f"🪙 -{result['cost']} coin "
                    f"({new_balance})"
                ),
                reply_markup=main_menu_keyboard(lang),
            )

            return

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

    if tg_file.file_path.startswith("http"):
        image_url = tg_file.file_path
    else:
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
                f"{style_label(style_key, lang)}\n\n"
                f"🪙 -{COIN_COST_STYLE} coin "
                f"({new_balance})"
            ),
            reply_markup=main_menu_keyboard(
                lang
            ),
        )

    except Exception:

        logger.exception(
            "fal.ai stil qo'llash xatosi:"
        )

        await notify_admin_error(
            context,
            f"Stil qo'llash — {style_key}",
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

    # MUHIM (YANGI): matn so'rashdan oldin ayol/erkak ovozini
    # tanlashni so'raymiz.
    await update.message.reply_text(
        t(
            lang,
            "voice_choose_gender",
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        t(lang, "voice_gender_female_btn"),
                        callback_data="voice_gender:female",
                    ),
                    InlineKeyboardButton(
                        t(lang, "voice_gender_male_btn"),
                        callback_data="voice_gender:male",
                    ),
                ]
            ]
        ),
    )


async def voice_gender_selected_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    chat_id = query.message.chat_id

    lang = get_lang(chat_id)

    gender = query.data.split(":", 1)[1]

    if gender not in ("female", "male"):
        return

    voice_gender_choice[chat_id] = gender

    awaiting_voice_text[chat_id] = True

    await query.message.reply_text(
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

        gender = voice_gender_choice.pop(
            chat_id,
            "female",
        )

        selected_voice = get_tts_voice(
            lang,
            gender,
        )

        communicate = edge_tts.Communicate(
            text,
            selected_voice,
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

    except Exception:

        logger.exception(
            "edge-tts xatosi:"
        )

        await notify_admin_error(
            context,
            "Ovoz yaratish (edge-tts)",
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

    except Exception:

        logger.exception(
            "fal.ai qo'shiq yaratish xatosi:"
        )

        await notify_admin_error(
            context,
            "Qo'shiq yaratish",
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

        video_url = await generate_fal_video(
            prompt,
            model_key,
        )

        if not video_url:

            raise ValueError(
                "Video URL topilmadi."
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

    except Exception:

        logger.exception(
            "fal.ai video yaratish xatosi:"
        )

        await notify_admin_error(
            context,
            "Video yaratish",
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

    if not FAL_KEY or "BU_YERGA" in FAL_KEY:

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
            await generate_fal_image(
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

    except Exception:

        logger.exception(
            "Higgsfield rasm yaratish xatosi:"
        )

        await notify_admin_error(
            context,
            "Rasm yaratish",
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

    if awaiting_voice_text.get(
        chat_id
    ):

        awaiting_voice_text[
            chat_id
        ] = False

        await generate_voice_from_text(
            update,
