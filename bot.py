"""
MUBORAKXON — Telegram AI Bot
- Claude text chat
- fal.ai FLUX image generation
- fal.ai FLUX image-to-image styles
- fal.ai video/music
- free edge-tts voice
- persistent coin system
- admin statistics

Railway Variables:
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
DATA_DIR=/data   # Railway Volume mount point
"""

import os
import io
import json
import asyncio
import logging
import traceback
import threading
import datetime

import httpx
import fal_client
import edge_tts
from anthropic import Anthropic

from i18n import t, LANGUAGES, DEFAULT_LANGUAGE

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

# ============================================================
# SETTINGS
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FAL_KEY = os.environ.get("FAL_KEY", "")
HF_API_KEY_ID = os.environ.get("HF_API_KEY_ID", "")
HF_API_KEY_SECRET = os.environ.get("HF_API_KEY_SECRET", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
PAYMENT_CARD_NUMBER = os.environ.get("PAYMENT_CARD_NUMBER", "8600 XXXX XXXX XXXX")
PAYMENT_CARD_OWNER = os.environ.get("PAYMENT_CARD_OWNER", "F.I.SH.")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "@sizning_username")
COIN_PRICE_SOM = int(os.environ.get("COIN_PRICE_SOM", "400"))
COIN_PRICE_RUB = float(os.environ.get("COIN_PRICE_RUB", "3"))

BOT_NAME = "MUBORAKXON"
WELCOME_IMAGE_PATH = "welcome.jpg"
MODEL_NAME = "claude-sonnet-4-6"

TTS_VOICE_MAP = {
    "uz": "uz-UZ-MadinaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "kk": "kk-KZ-AigulNeural",
    "en": "en-US-JennyNeural",
    "tg": "ru-RU-SvetlanaNeural",
    "ky": "ru-RU-SvetlanaNeural",
}
DEFAULT_TTS_VOICE = "uz-UZ-MadinaNeural"

IMAGE_MODEL_ID = "fal-ai/flux/dev"
STYLE_MODEL_ID = "fal-ai/flux/dev/image-to-image"
MUSIC_MODEL_ID = "fal-ai/minimax-music"

VIDEO_MODELS = {
    "wan": {"label": "🟢 Wan 2.6 (arzon)", "model_id": "fal-ai/wan-t2v"},
    "kling": {
        "label": "🔵 Kling 1.6 (sifatli)",
        "model_id": "fal-ai/kling-video/v1.6/standard/text-to-video",
    },
}

FAL_ASPECT_TO_IMAGE_SIZE = {
    "1:1": "square_hd",
    "9:16": "portrait_16_9",
    "16:9": "landscape_16_9",
    "3:4": "portrait_4_3",
    "4:3": "landscape_4_3",
    "3:2": "landscape_4_3",
    "2:3": "portrait_4_3",
}

COIN_START_BALANCE = 50
COIN_COST_TEXT = 1
COIN_COST_IMAGE = 10
COIN_COST_STYLE = 10
COIN_COST_VIDEO = 50
COIN_COST_VOICE = 3
COIN_COST_MUSIC = 15
DAILY_BONUS_AMOUNT = 10

# ============================================================
# PERSISTENT DATA
# ============================================================
# Railway'da DATA_DIR=/data qilib, /data ga Volume biriktiring.
DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

COINS_FILE = os.path.join(DATA_DIR, "coins.json")
COINS_BACKUP_FILE = os.path.join(DATA_DIR, "coins_backup.json")
BONUS_FILE = os.path.join(DATA_DIR, "daily_bonus.json")
LANG_FILE = os.path.join(DATA_DIR, "user_languages.json")

# RLock: bir vaqtning o'zida bir nechta update coin faylini buzmasin.
coins_lock = threading.RLock()

SYSTEM_PROMPT = (
    "Sen foydali, samimiy va bilimdon sun'iy intellekt yordamchisisan, "
    "isming Muborakxon. Foydalanuvchi bilan o'zbek tilida "
    "(agar u boshqa tilda yozmasa) muloqot qilasan. "
    "Javoblaring aniq, tushunarli va foydali bo'lsin."
)
MAX_HISTORY_MESSAGES = 20

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
os.environ["FAL_KEY"] = FAL_KEY

conversation_history = {}
awaiting_image_prompt = {}
awaiting_video_model_choice = {}
awaiting_video_prompt = {}
awaiting_voice_text = {}
awaiting_music_prompt = {}
awaiting_style_photo = {}

# ============================================================
# ERROR REPORTING
# ============================================================

async def notify_admin_error(context, title):
    if not ADMIN_ID or "BU_YERGA" in ADMIN_ID:
        return
    tb_text = traceback.format_exc()
    if len(tb_text) > 3500:
        tb_text = "...\n" + tb_text[-3500:]
    try:
        await context.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=f"🔴 XATOLIK: {title}\n\n```\n{tb_text}\n```",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning("Admin xabarini yuborib bo'lmadi: %s", e)

# ============================================================
# LANGUAGE
# ============================================================

def load_languages():
    if not os.path.exists(LANG_FILE):
        return {}
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.exception("Language fayli o'qilmadi")
        return {}

def save_languages(data):
    tmp = LANG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LANG_FILE)

def get_lang(user_id):
    return load_languages().get(str(user_id), DEFAULT_LANGUAGE)

def set_lang(user_id, lang):
    data = load_languages()
    data[str(user_id)] = lang
    save_languages(data)

def language_inline_keyboard():
    buttons, row = [], []
    for code, label in LANGUAGES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ============================================================
# BONUS
# ============================================================

def load_bonus_data():
    if not os.path.exists(BONUS_FILE):
        return {}
    try:
        with open(BONUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.exception("Bonus fayli o'qilmadi")
        return {}

def save_bonus_data(data):
    tmp = BONUS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, BONUS_FILE)

def can_claim_bonus(user_id):
    data = load_bonus_data()
    last_claim = data.get(str(user_id))
    if not last_claim:
        return True
    try:
        return datetime.date.fromisoformat(last_claim) < datetime.date.today()
    except ValueError:
        return True

def mark_bonus_claimed(user_id):
    data = load_bonus_data()
    data[str(user_id)] = datetime.date.today().isoformat()
    save_bonus_data(data)

# ============================================================
# COINS — SAFE / PERSISTENT
# ============================================================
# MUHIM:
# 1. Til almashtirish coinlarni o'zgartirmaydi.
# 2. coins.json buzilsa backupdan tiklashga urinadi.
# 3. Yangi user bo'lmasa faqat o'sha userga 50 coin beradi.
# 4. Faylni atomik yozadi.
# 5. RLock parallel update'larda ma'lumot yo'qolishini kamaytiradi.

def _read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} JSON object emas")
    return data

def load_coins():
    with coins_lock:
        if os.path.exists(COINS_FILE):
            try:
                return _read_json_file(COINS_FILE)
            except Exception:
                logger.exception("coins.json o'qilmadi; backup tekshiriladi")

        if os.path.exists(COINS_BACKUP_FILE):
            try:
                data = _read_json_file(COINS_BACKUP_FILE)
                logger.warning("coins_backup.json dan coinlar tiklandi")
                return data
            except Exception:
                logger.exception("coins_backup.json ham o'qilmadi")

        # Ikkala fayl ham yo'q bo'lsa — bu birinchi ishga tushish.
        # Mavjud fayl buzilgan bo'lsa jim turib hammani 50 ga tushirmaymiz.
        if os.path.exists(COINS_FILE) or os.path.exists(COINS_BACKUP_FILE):
            raise RuntimeError(
                "Coin fayllari o'qilmadi. Coinlar xavfsizligi uchun "
                "avtomatik 50 coin berish to'xtatildi."
            )
        return {}

def save_coins(data):
    with coins_lock:
        # Avval amaldagi sog'lom coins.json ni backup qilamiz.
        if os.path.exists(COINS_FILE):
            try:
                current = _read_json_file(COINS_FILE)
                backup_tmp = COINS_BACKUP_FILE + ".tmp"
                with open(backup_tmp, "w", encoding="utf-8") as f:
                    json.dump(current, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(backup_tmp, COINS_BACKUP_FILE)
            except Exception:
                logger.exception("Coin backup yozilmadi")

        tmp = COINS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, COINS_FILE)

def get_balance(user_id):
    uid = str(user_id)
    with coins_lock:
        coins = load_coins()
        if uid not in coins:
            coins[uid] = COIN_START_BALANCE
            save_coins(coins)
        try:
            return int(coins[uid])
        except (ValueError, TypeError):
            coins[uid] = COIN_START_BALANCE
            save_coins(coins)
            return COIN_START_BALANCE

def change_balance(user_id, amount):
    uid = str(user_id)
    with coins_lock:
        coins = load_coins()
        if uid not in coins:
            coins[uid] = COIN_START_BALANCE
        try:
            coins[uid] = int(coins[uid])
        except (ValueError, TypeError):
            coins[uid] = COIN_START_BALANCE
        coins[uid] += int(amount)
        if coins[uid] < 0:
            coins[uid] = 0
        save_coins(coins)
        return int(coins[uid])

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def escape_markdown_v1(text):
    if text is None:
        return ""
    for char in ("_", "*", "`", "["):
        text = text.replace(char, "\\" + char)
    return text

# ============================================================
# MENUS
# ============================================================

def main_menu_keyboard(lang=DEFAULT_LANGUAGE):
    return ReplyKeyboardMarkup([
        [KeyboardButton(t(lang, "btn_new_chat")), KeyboardButton(t(lang, "btn_styles"))],
        [KeyboardButton(t(lang, "btn_image")), KeyboardButton(t(lang, "btn_video"))],
        [KeyboardButton(t(lang, "btn_voice")), KeyboardButton(t(lang, "btn_music"))],
        [KeyboardButton(t(lang, "btn_balance")), KeyboardButton(t(lang, "btn_bonus"))],
        [KeyboardButton(t(lang, "btn_buy_coins")), KeyboardButton(t(lang, "btn_settings"))],
        [KeyboardButton(t(lang, "btn_help")), KeyboardButton(t(lang, "btn_language"))],
    ], resize_keyboard=True)

def video_model_keyboard(lang=DEFAULT_LANGUAGE):
    return ReplyKeyboardMarkup([
        [KeyboardButton(t(lang, "video_model_wan"))],
        [KeyboardButton(t(lang, "video_model_kling"))],
    ], resize_keyboard=True)

# ============================================================
# STYLES
# ============================================================

STYLE_TEMPLATES = {
    "bw_portrait": {"label": "🖤 Qora-oq portret",
        "prompt": "Transform the provided photo into a dramatic black and white portrait, moody lighting, high contrast, cinematic shadows, professional studio photography. Preserve the person's identity and facial features."},
    "cinematic_car": {"label": "🚗 Kinematik avtomobil",
        "prompt": "Transform the provided photo into cinematic automotive photography, dramatic lighting, film grain, wide angle, moody atmosphere, professional car advertisement style. Preserve the original car."},
    "vintage_sketch": {"label": "✏️ Vintage eskiz",
        "prompt": "Transform the provided photo into a detailed vintage pencil sketch, cross-hatching shading, hand-drawn artistic illustration style. Preserve the original subject and composition."},
    "golden_hour": {"label": "🌅 Oltin soat portreti",
        "prompt": "Transform the provided photo into a beautiful golden hour portrait, warm sunset lighting, soft bokeh background, natural cinematic photography. Preserve the person's identity and facial features."},
    "figurine": {"label": "🧸 Miniatura figurka",
        "prompt": "Transform the provided subject into a hyper-realistic collectible figurine, detailed miniature toy style, product photography, studio lighting. Preserve recognizable features."},
    "fantasy_armor": {"label": "⚔️ Fentezi zirh",
        "prompt": "Transform the provided portrait into an epic fantasy warrior wearing detailed medieval armor, cinematic fog, epic lighting, film still aesthetic. Preserve the person's identity and facial features."},
    "mini_statue_desk": {"label": "🏆 Mini haykalcha (stolda)",
        "prompt": "Transform the provided photo into a professional business portrait of the person sitting at a modern office desk, confidently holding a small collectible figurine that looks like them in the palm of their hand. Sharp studio lighting, shallow depth of field, modern office background. Preserve identity and facial features."},
    "ink_portrait_color": {"label": "🖊 Rangli siyoh portret",
        "prompt": "Transform the provided photo into a detailed colored ink and pencil illustration portrait, fine crosshatching line work combined with selective color accents on clothing, hand-drawn editorial illustration style. Preserve the person's identity and facial features."},
    "clone_multiply": {"label": "👥 Klon effekti",
        "prompt": "Transform the provided photo into a surreal multiplicity composition showing five identical copies of the same person standing and sitting in different natural poses across an open plaza, cinematic photography, consistent lighting. Preserve identity and facial features in every copy."},
}

def styles_inline_keyboard():
    buttons, row = [], []
    for key, info in STYLE_TEMPLATES.items():
        row.append(InlineKeyboardButton(info["label"], callback_data=f"style:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

# ============================================================
# AI HELPERS
# ============================================================

async def translate_prompt_to_english(text):
    try:
        response = await asyncio.to_thread(
            claude_client.messages.create,
            model=MODEL_NAME,
            max_tokens=200,
            system=(
                "Translate the short image/video prompt into natural vivid English. "
                "Output ONLY the translated prompt."
            ),
            messages=[{"role": "user", "content": text}],
        )
        translated = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        return translated or text
    except Exception as e:
        logger.warning("Prompt tarjimasi xatosi: %s", e)
        return text

async def generate_fal_image(prompt, aspect_ratio="1:1"):
    english_prompt = await translate_prompt_to_english(prompt)
    image_size = FAL_ASPECT_TO_IMAGE_SIZE.get(aspect_ratio, "square_hd")

    def run():
        return fal_client.subscribe(
            IMAGE_MODEL_ID,
            arguments={"prompt": english_prompt, "image_size": image_size},
        )

    result = await asyncio.to_thread(run)
    if not isinstance(result, dict):
        return None
    images = result.get("images") or []
    if not images:
        return None
    first = images[0]
    return first.get("url") if isinstance(first, dict) else None

async def generate_fal_video(prompt, model_id):
    english_prompt = await translate_prompt_to_english(prompt)

    def run():
        return fal_client.subscribe(model_id, arguments={"prompt": english_prompt})

    result = await asyncio.to_thread(run)
    if not isinstance(result, dict):
        return None
    video = result.get("video")
    if isinstance(video, dict):
        return video.get("url")
    return result.get("video_url")

async def generate_fal_music(prompt):
    english_prompt = await translate_prompt_to_english(prompt)

    def run():
        return fal_client.subscribe(MUSIC_MODEL_ID, arguments={"prompt": english_prompt})

    result = await asyncio.to_thread(run)
    if not isinstance(result, dict):
        return None
    audio = result.get("audio")
    if isinstance(audio, dict):
        return audio.get("url")
    return result.get("audio_url")

async def download_telegram_image(image_url):
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(image_url)
        resp.raise_for_status()
        return resp.content

# ============================================================
# STYLE IMAGE-TO-IMAGE
# ============================================================

async def apply_fal_ai_style(image_bytes, style_prompt):
    """
    fal-ai/flux/dev/image-to-image
    strength = 0.65
    image_size = square_hd
    """

    def run():
        image_url = fal_client.upload(
            image_bytes,
            "image/jpeg",
            "image.jpg",
        )

        result = fal_client.subscribe(
            STYLE_MODEL_ID,
            arguments={
                "image_url": image_url,
                "prompt": style_prompt,
                "strength": 0.65,
                "image_size": "square_hd",
            },
        )

        if not isinstance(result, dict):
            return None

        images = result.get("images") or []
        if not images:
            return None

        first = images[0]
        return first.get("url") if isinstance(first, dict) else None

    return await asyncio.to_thread(run)

# ============================================================
# START / WELCOME
# ============================================================

async def start(update, context):
    chat_id = update.effective_chat.id

    conversation_history[chat_id] = []
    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt.pop(chat_id, None)
    awaiting_voice_text[chat_id] = False
    awaiting_music_prompt[chat_id] = False
    awaiting_style_photo.pop(chat_id, None)

    if str(chat_id) not in load_languages():
        await update.message.reply_text(
            t(DEFAULT_LANGUAGE, "choose_language"),
            reply_markup=language_inline_keyboard(),
        )
        return

    await send_welcome(update, context, chat_id)

async def send_welcome(update, context, chat_id, balance=None):
    lang = get_lang(chat_id)
    # Agar callback ichidan oldindan o'qilgan balance berilsa,
    # til almashtirish paytida coin fayliga qayta tegilmaydi.
    if balance is None:
        balance = get_balance(chat_id)

    caption = t(
        lang, "welcome",
        bot_name=BOT_NAME,
        start_balance=COIN_START_BALANCE,
        balance=balance,
    )

    if os.path.exists(WELCOME_IMAGE_PATH):
        with open(WELCOME_IMAGE_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(lang),
            )
    else:
        await update.message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# LANGUAGE CHANGE — COINNI O'ZGARTIRMAYDI
# ============================================================

async def language_selected_callback(update, context):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    lang_code = query.data.split(":", 1)[1]

    if lang_code not in LANGUAGES:
        return

    # BALANCE NI TILNI O'ZGARTIRISHDAN OLDIN BIR MARTA O'QIYMIZ.
    # Keyin send_welcome shu qiymatdan foydalanadi.
    balance = get_balance(chat_id)

    set_lang(chat_id, lang_code)

    await query.message.reply_text(
        t(lang_code, "language_set")
    )

    class _FakeUpdate:
        pass

    fake = _FakeUpdate()
    fake.message = query.message

    await send_welcome(
        fake,
        context,
        chat_id,
        balance=balance,
    )

# ============================================================
# BASIC COMMANDS
# ============================================================

async def show_id(update, context):
    await update.message.reply_text(
        f"🆔 Sizning Telegram ID'ingiz: `{update.effective_user.id}`",
        parse_mode="Markdown",
    )

async def show_balance(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)
    await update.message.reply_text(
        f"💰 {balance} coin\n\n"
        f"💬 {COIN_COST_TEXT}  🎨 {COIN_COST_IMAGE}  "
        f"🎬 {COIN_COST_VIDEO}  🔊 {COIN_COST_VOICE}  "
        f"🎵 {COIN_COST_MUSIC}",
        reply_markup=main_menu_keyboard(lang),
    )

async def help_command(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    await update.message.reply_text(
        t(lang, "help_text"),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(lang),
    )

async def settings_command(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    await update.message.reply_text(
        t(lang, "settings_text", bot_name=BOT_NAME, model=MODEL_NAME, tts_model="edge-tts"),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(lang),
    )

async def new_chat(update, context):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt.pop(chat_id, None)
    awaiting_voice_text[chat_id] = False
    awaiting_music_prompt[chat_id] = False
    awaiting_style_photo.pop(chat_id, None)

    lang = get_lang(chat_id)
    await update.message.reply_text(
        t(lang, "new_chat_started"),
        reply_markup=main_menu_keyboard(lang),
    )

# ============================================================
# BUY COINS
# ============================================================

async def show_buy_coins(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    price_100_som = COIN_PRICE_SOM * 100

    try:
        await update.message.reply_text(
            t(
                lang, "buy_coins_info",
                price_som=COIN_PRICE_SOM,
                price_rub=COIN_PRICE_RUB,
                price_100_som=f"{price_100_som:,}".replace(",", " "),
                card_number=escape_markdown_v1(PAYMENT_CARD_NUMBER),
                card_owner=escape_markdown_v1(PAYMENT_CARD_OWNER),
                admin_username=escape_markdown_v1(ADMIN_USERNAME),
                user_id=chat_id,
            ),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        logger.exception("show_buy_coins xatosi")
        await update.message.reply_text(
            t(
                lang, "buy_coins_info",
                price_som=COIN_PRICE_SOM,
                price_rub=COIN_PRICE_RUB,
                price_100_som=f"{price_100_som:,}".replace(",", " "),
                card_number=PAYMENT_CARD_NUMBER,
                card_owner=PAYMENT_CARD_OWNER,
                admin_username=ADMIN_USERNAME,
                user_id=chat_id,
            ),
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# ADMIN
# ============================================================

async def add_coins_admin(update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Foydalanish:\n/coin_qoshish <foydalanuvchi_id> <miqdor>\n\n"
            "Masalan:\n/coin_qoshish 123456789 100"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except (ValueError, TypeError):
        await update.message.reply_text("❌ ID va miqdor raqam bo'lishi kerak.")
        return

    if amount == 0:
        await update.message.reply_text("❌ Coin miqdori 0 bo'lishi mumkin emas.")
        return

    new_balance = change_balance(target_id, amount)
    action = f"{amount} coin qo'shildi" if amount > 0 else f"{abs(amount)} coin ayirildi"

    await update.message.reply_text(
        f"✅ Foydalanuvchi {target_id} hisobida {action}.\n"
        f"💰 Yangi balans: {new_balance}"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎉 Hisobingiz o'zgartirildi!\n\n"
                 f"🪙 O'zgarish: {amount:+d} coin\n"
                 f"💰 Yangi balans: {new_balance}",
        )
    except Exception as e:
        logger.warning("Userga coin xabari yuborilmadi: %s", e)

async def show_stats_admin(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return

    coins = load_coins()
    users_count = len(coins)
    total_coins = 0
    for balance in coins.values():
        try:
            total_coins += int(balance)
        except (ValueError, TypeError):
            pass

    await update.message.reply_text(
        "📊 *BOT STATISTIKASI*\n\n"
        f"👥 Foydalanuvchilar: *{users_count}*\n"
        f"🪙 Jami coin: *{total_coins}*",
        parse_mode="Markdown",
    )

# ============================================================
# STYLES
# ============================================================

async def show_styles_menu(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_STYLE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_STYLE, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await update.message.reply_text(
        t(lang, "choose_style"),
        reply_markup=styles_inline_keyboard(),
    )

async def style_selected_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = get_lang(chat_id)
    style_key = query.data.split(":", 1)[1]

    if style_key not in STYLE_TEMPLATES:
        return

    awaiting_style_photo[chat_id] = style_key
    await query.message.reply_text(
        t(lang, "style_selected", label=STYLE_TEMPLATES[style_key]["label"])
    )

async def process_style_photo(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    style_key = awaiting_style_photo.pop(chat_id, None)

    if not style_key:
        return

    balance = get_balance(chat_id)
    if balance < COIN_COST_STYLE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_STYLE, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text(t(lang, "style_applying"))

    try:
        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        image_url = (
            "https://api.telegram.org/file/bot"
            f"{TELEGRAM_BOT_TOKEN}/{tg_file.file_path}"
        )
        image_bytes = await download_telegram_image(image_url)

        result_url = await apply_fal_ai_style(
            image_bytes,
            STYLE_TEMPLATES[style_key]["prompt"],
        )

        if not result_url:
            raise ValueError("fal.ai rasm URL qaytarmadi")

        new_balance = change_balance(chat_id, -COIN_COST_STYLE)

        await update.message.reply_photo(
            photo=result_url,
            caption=(
                f"🖼 {STYLE_TEMPLATES[style_key]['label']}\n\n"
                f"🪙 -{COIN_COST_STYLE} coin ({new_balance})"
            ),
            reply_markup=main_menu_keyboard(lang),
        )

    except Exception:
        logger.exception("Stil qo'llash xatosi")
        await notify_admin_error(context, f"Stil qo'llash — {style_key}")
        await update.message.reply_text(
            t(lang, "style_error"),
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# DAILY BONUS
# ============================================================

async def claim_daily_bonus(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)

    if not can_claim_bonus(chat_id):
        await update.message.reply_text(
            t(lang, "bonus_already_claimed"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    mark_bonus_claimed(chat_id)
    new_balance = change_balance(chat_id, DAILY_BONUS_AMOUNT)

    await update.message.reply_text(
        t(lang, "bonus_claimed", amount=DAILY_BONUS_AMOUNT, balance=new_balance),
        reply_markup=main_menu_keyboard(lang),
    )

# ============================================================
# IMAGE
# ============================================================

async def ask_image_prompt(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_IMAGE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_IMAGE, balance=balance)
        )
        return

    awaiting_image_prompt[chat_id] = True
    await update.message.reply_text(t(lang, "image_prompt_ask"), parse_mode="Markdown")

async def generate_image_from_prompt(update, context, prompt):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_IMAGE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_IMAGE, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    if not FAL_KEY:
        await update.message.reply_text(
            t(lang, "hf_not_configured"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text(t(lang, "image_generating"))

    try:
        image_url = await generate_fal_image(prompt)
        if not image_url:
            raise ValueError("fal.ai rasm URL qaytarmadi")

        new_balance = change_balance(chat_id, -COIN_COST_IMAGE)

        await update.message.reply_photo(
            photo=image_url,
            caption=f"🖼 {prompt}\n\n🪙 -{COIN_COST_IMAGE} coin ({new_balance})",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        logger.exception("Rasm yaratish xatosi")
        await notify_admin_error(context, "Rasm yaratish")
        await update.message.reply_text(
            t(lang, "image_error"),
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# VIDEO
# ============================================================

async def ask_video_model(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_VIDEO:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_VIDEO, balance=balance)
        )
        return

    awaiting_video_model_choice[chat_id] = True
    await update.message.reply_text(
        t(lang, "video_choose_model"),
        reply_markup=video_model_keyboard(lang),
    )

async def ask_video_prompt(update, context, model_key):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt[chat_id] = model_key

    await update.message.reply_text(
        t(lang, "video_prompt_ask"),
        parse_mode="Markdown",
    )

async def generate_video_from_prompt(update, context, prompt, model_key):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_VIDEO:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_VIDEO, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    model_info = VIDEO_MODELS[model_key]
    await context.bot.send_chat_action(chat_id=chat_id, action="record_video")
    await update.message.reply_text(
        t(lang, "video_generating", label=model_info["label"]),
        reply_markup=main_menu_keyboard(lang),
    )

    try:
        video_url = await generate_fal_video(prompt, model_info["model_id"])
        if not video_url:
            raise ValueError("Video URL topilmadi")

        new_balance = change_balance(chat_id, -COIN_COST_VIDEO)
        await update.message.reply_video(
            video=video_url,
            caption=f"🎬 {prompt}\n\n🪙 -{COIN_COST_VIDEO} coin ({new_balance})",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        logger.exception("Video xatosi")
        await notify_admin_error(context, "Video yaratish")
        await update.message.reply_text(
            t(lang, "video_error"),
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# VOICE
# ============================================================

async def ask_voice_text(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_VOICE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_VOICE, balance=balance)
        )
        return

    awaiting_voice_text[chat_id] = True
    await update.message.reply_text(t(lang, "voice_ask_text"), parse_mode="Markdown")

async def generate_voice_from_text(update, context, text):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_VOICE:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_VOICE, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    await update.message.reply_text(t(lang, "voice_generating"))

    audio_path = f"/tmp/voice_{chat_id}.mp3"

    try:
        voice = TTS_VOICE_MAP.get(lang, DEFAULT_TTS_VOICE)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise ValueError("edge-tts audio fayl yaratmadi")

        new_balance = change_balance(chat_id, -COIN_COST_VOICE)

        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(
                voice=audio,
                caption=f"🔊 -{COIN_COST_VOICE} coin ({new_balance})",
                reply_markup=main_menu_keyboard(lang),
            )
    except Exception:
        logger.exception("edge-tts xatosi")
        await notify_admin_error(context, "Ovoz yaratish")
        await update.message.reply_text(
            t(lang, "voice_error"),
            reply_markup=main_menu_keyboard(lang),
        )
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

# ============================================================
# MUSIC
# ============================================================

async def ask_music_prompt(update, context):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_MUSIC:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_MUSIC, balance=balance)
        )
        return

    awaiting_music_prompt[chat_id] = True
    await update.message.reply_text(t(lang, "music_ask_prompt"), parse_mode="Markdown")

async def generate_music_from_prompt(update, context, prompt):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    balance = get_balance(chat_id)

    if balance < COIN_COST_MUSIC:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_MUSIC, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    await update.message.reply_text(t(lang, "music_generating"))

    try:
        audio_url = await generate_fal_music(prompt)
        if not audio_url:
            raise ValueError("Audio URL topilmadi")

        new_balance = change_balance(chat_id, -COIN_COST_MUSIC)

        await update.message.reply_audio(
            audio=audio_url,
            caption=f"🎵 {prompt}\n\n🪙 -{COIN_COST_MUSIC} coin ({new_balance})",
            reply_markup=main_menu_keyboard(lang),
        )
    except Exception:
        logger.exception("Musiqa xatosi")
        await notify_admin_error(context, "Qo'shiq yaratish")
        await update.message.reply_text(
            t(lang, "music_error"),
            reply_markup=main_menu_keyboard(lang),
        )

# ============================================================
# MAIN MESSAGE
# ============================================================

async def handle_message(update, context):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    lang = get_lang(chat_id)

    if user_text == t(lang, "btn_new_chat"):
        await new_chat(update, context); return
    if user_text == t(lang, "btn_styles"):
        await show_styles_menu(update, context); return
    if user_text == t(lang, "btn_image"):
        await ask_image_prompt(update, context); return
    if user_text == t(lang, "btn_video"):
        await ask_video_model(update, context); return
    if user_text == t(lang, "btn_voice"):
        await ask_voice_text(update, context); return
    if user_text == t(lang, "btn_music"):
        await ask_music_prompt(update, context); return
    if user_text == t(lang, "btn_balance"):
        await show_balance(update, context); return
    if user_text == t(lang, "btn_bonus"):
        await claim_daily_bonus(update, context); return
    if user_text == t(lang, "btn_buy_coins"):
        await show_buy_coins(update, context); return
    if user_text == t(lang, "btn_settings"):
        await settings_command(update, context); return
    if user_text == t(lang, "btn_help"):
        await help_command(update, context); return
    if user_text == t(lang, "btn_language"):
        await update.message.reply_text(
            t(DEFAULT_LANGUAGE, "choose_language"),
            reply_markup=language_inline_keyboard(),
        )
        return

    if awaiting_video_model_choice.get(chat_id):
        if user_text == t(lang, "video_model_wan"):
            await ask_video_prompt(update, context, "wan"); return
        if user_text == t(lang, "video_model_kling"):
            await ask_video_prompt(update, context, "kling"); return
        await update.message.reply_text(
            t(lang, "choose_button_below"),
            reply_markup=video_model_keyboard(lang),
        )
        return

    if chat_id in awaiting_video_prompt:
        model_key = awaiting_video_prompt.pop(chat_id)
        await generate_video_from_prompt(update, context, user_text, model_key)
        return

    if awaiting_image_prompt.get(chat_id):
        awaiting_image_prompt[chat_id] = False
        await generate_image_from_prompt(update, context, user_text)
        return

    if awaiting_voice_text.get(chat_id):
        awaiting_voice_text[chat_id] = False
        await generate_voice_from_text(update, context, user_text)
        return

    if awaiting_music_prompt.get(chat_id):
        awaiting_music_prompt[chat_id] = False
        await generate_music_from_prompt(update, context, user_text)
        return

    balance = get_balance(chat_id)
    if balance < COIN_COST_TEXT:
        await update.message.reply_text(
            t(lang, "insufficient_coins", cost=COIN_COST_TEXT, balance=balance),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})
    if len(history) > MAX_HISTORY_MESSAGES:
        history[:] = history[-MAX_HISTORY_MESSAGES:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    lang_names = {
        "uz": "o'zbek", "ru": "русском", "kk": "қазақ",
        "tg": "тоҷикӣ", "ky": "кыргыз", "en": "English",
    }
    lang_name = lang_names.get(lang, "o'zbek")

    try:
        response = await asyncio.to_thread(
            claude_client.messages.create,
            model=MODEL_NAME,
            max_tokens=1024,
            system=SYSTEM_PROMPT + f" Javobingizni {lang_name} tilida yozing.",
            messages=history,
        )
        reply_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
    except Exception:
        logger.exception("Anthropic API xatosi")
        await notify_admin_error(context, "Claude chat")
        await update.message.reply_text(
            t(lang, "text_error"),
            reply_markup=main_menu_keyboard(lang),
        )
        return

    history.append({"role": "assistant", "content": reply_text})
    conversation_history[chat_id] = history
    change_balance(chat_id, -COIN_COST_TEXT)

    await update.message.reply_text(
        reply_text,
        reply_markup=main_menu_keyboard(get_lang(chat_id)),
    )

# ============================================================
# BUILD / MAIN
# ============================================================

def build_application():
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not ANTHROPIC_API_KEY: missing.append("ANTHROPIC_API_KEY")
    if not FAL_KEY: missing.append("FAL_KEY")
    if not HF_API_KEY_ID or not HF_API_KEY_SECRET:
        missing.append("HF_API_KEY_ID / HF_API_KEY_SECRET")
    if not ADMIN_ID: missing.append("ADMIN_ID")

    if missing:
        print("⚠️ Sozlanmagan Variables:", ", ".join(missing))

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", new_chat))
    app.add_handler(CommandHandler("id", show_id))
    app.add_handler(CommandHandler("balance", show_balance))
    app.add_handler(CommandHandler("coin_qoshish", add_coins_admin))
    app.add_handler(CommandHandler("statistika", show_stats_admin))

    app.add_handler(CallbackQueryHandler(style_selected_callback, pattern=r"^style:"))
    app.add_handler(CallbackQueryHandler(language_selected_callback, pattern=r"^lang:"))

    app.add_handler(MessageHandler(filters.PHOTO, process_style_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app

def main():
    app = build_application()
    print(f"🤖 {BOT_NAME} ishga tushdi.")
    app.run_polling()

if __name__ == "__main__":
    main()
