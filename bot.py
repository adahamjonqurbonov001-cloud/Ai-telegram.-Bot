"""
Sun'iy Intellekt Telegram Bot (Suzma AI uslubida, tugmali menyu va coin tizimi bilan)
- Matnli suhbat: Claude (Anthropic) API orqali
- Rasm yaratish: OpenAI (DALL-E) API orqali
- Video yaratish: fal.ai orqali (Wan 2.6 yoki Kling 1.6)
- Matnni ovozga aylantirish: OpenAI TTS orqali
- Coin tizimi: har bir amal uchun coin yechiladi, admin qo'lda coin qo'shishi mumkin

O'rnatish:
    pip install python-telegram-bot anthropic openai fal-client --upgrade

Ishga tushirish:
    python bot.py

Muhit o'zgaruvchilari orqali kalitlarni bering:
    TELEGRAM_BOT_TOKEN
    ANTHROPIC_API_KEY
    OPENAI_API_KEY
    FAL_KEY
    ADMIN_ID
"""

import os
import json
import logging
import asyncio
import fal_client
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from anthropic import Anthropic
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "BU_YERGA_TELEGRAM_TOKENINGIZNI_YOZING")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "BU_YERGA_ANTHROPIC_API_KEYINGIZNI_YOZING")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "BU_YERGA_OPENAI_API_KEYINGIZNI_YOZING")
FAL_KEY = os.environ.get("FAL_KEY", "BU_YERGA_FAL_API_KEYINGIZNI_YOZING")
ADMIN_ID = os.environ.get("ADMIN_ID", "BU_YERGA_TELEGRAM_ID_INGIZNI_YOZING")

MODEL_NAME = "claude-sonnet-4-6"
IMAGE_MODEL_NAME = "dall-e-3"
TTS_MODEL_NAME = "tts-1"
TTS_VOICE = "alloy"  # boshqa variantlar: echo, fable, onyx, nova, shimmer

VIDEO_MODELS = {
    "wan": {"label": "🟢 Wan 2.6 (arzon)", "model_id": "fal-ai/wan-t2v"},
    "kling": {"label": "🔵 Kling 1.6 (sifatli)", "model_id": "fal-ai/kling-video/v1.6/standard/text-to-video"},
}

MUSIC_MODEL_ID = "fal-ai/minimax-music"  # fal.ai saytida aniq nomi tekshirilishi kerak

COIN_START_BALANCE = 50
COIN_COST_TEXT = 1
COIN_COST_IMAGE = 10
COIN_COST_VIDEO = 30
COIN_COST_VOICE = 3
COIN_COST_MUSIC = 15
COINS_FILE = "coins.json"

SYSTEM_PROMPT = (
    "Sen foydali, samimiy va bilimdon sun'iy intellekt yordamchisisan. "
    "Foydalanuvchi bilan o'zbek tilida (agar u boshqa tilda yozmasa) muloqot qilasan. "
    "Javoblaring aniq, tushunarli va foydali bo'lsin."
)

MAX_HISTORY_MESSAGES = 20

BTN_NEW_CHAT = "🆕 Yangi chat"
BTN_IMAGE = "🎨 Rasm yaratish"
BTN_VIDEO = "🎬 Video yaratish"
BTN_VOICE = "🔊 Matnni ovozga aylantirish"
BTN_MUSIC = "🎵 Qo'shiq yaratish"
BTN_BALANCE = "💰 Balans"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_HELP = "ℹ️ Yordam"
BTN_VIDEO_WAN = VIDEO_MODELS["wan"]["label"]
BTN_VIDEO_KLING = VIDEO_MODELS["kling"]["label"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
os.environ["FAL_KEY"] = FAL_KEY

conversation_history: dict[int, list[dict]] = {}
awaiting_image_prompt: dict[int, bool] = {}
awaiting_video_model_choice: dict[int, bool] = {}
awaiting_video_prompt: dict[int, str] = {}
awaiting_voice_text: dict[int, bool] = {}
awaiting_music_prompt: dict[int, bool] = {}


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


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_NEW_CHAT), KeyboardButton(BTN_IMAGE)],
            [KeyboardButton(BTN_VIDEO), KeyboardButton(BTN_VOICE)],
            [KeyboardButton(BTN_MUSIC), KeyboardButton(BTN_BALANCE)],
            [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def video_model_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_VIDEO_WAN)], [KeyboardButton(BTN_VIDEO_KLING)]],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt.pop(chat_id, None)
    awaiting_voice_text[chat_id] = False
    balance = get_balance(chat_id)
    await update.message.reply_text(
        "Salom! 👋 Men sun'iy intellekt asosida ishlaydigan botman.\n\n"
        f"🪙 Sizga {COIN_START_BALANCE} ta bepul coin berildi! Joriy balans: {balance}\n\n"
        "💬 Yozing — javob beraman (1 coin)\n"
        "🎨 Rasm yaratish (10 coin)\n"
        "🎬 Video yaratish (30 coin)\n"
        "🔊 Matnni ovozga aylantirish (3 coin)\n"
        "🎵 Qo'shiq yaratish (15 coin)\n\n"
        "Quyidagi menyudan foydalaning:",
        reply_markup=main_menu_keyboard(),
    )


async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Sizning Telegram ID'ingiz: `{user_id}`", parse_mode="Markdown")


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    balance = get_balance(chat_id)
    await update.message.reply_text(
        f"💰 Sizning balansingiz: *{balance} coin*\n\n"
        f"Narxlar:\n💬 Matn: {COIN_COST_TEXT} coin\n🎨 Rasm: {COIN_COST_IMAGE} coin\n"
        f"🎬 Video: {COIN_COST_VIDEO} coin\n🔊 Ovozga aylantirish: {COIN_COST_VOICE} coin\n🎵 Qo'shiq: {COIN_COST_MUSIC} coin\n\n"
        f"Coin sotib olish uchun admin bilan bog'laning.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def add_coins_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Foydalanish: /coin_qoshish <foydalanuvchi_id> <miqdor>")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("ID va miqdor raqam bo'lishi kerak.")
        return
    new_balance = change_balance(target_id, amount)
    await update.message.reply_text(f"✅ Foydalanuvchi {target_id} ga {amount} coin qo'shildi.\nYangi balans: {new_balance}")
    try:
        await context.bot.send_message(chat_id=target_id, text=f"🎉 Hisobingizga {amount} coin qo'shildi! Yangi balans: {new_balance}")
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborib bo'lmadi: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Yordam*\n\n🆕 Yangi chat — suhbat tarixini tozalaydi\n"
        "🎨 Rasm yaratish — tavsif asosida rasm chizadi (10 coin)\n"
        "🎬 Video yaratish — tavsif asosida qisqa video yaratadi (30 coin)\n"
        "🔊 Matnni ovozga aylantirish — istalgan matnni ovozli xabarga aylantiradi (3 coin)\n"
        "🎵 Qo'shiq yaratish — mavzu asosida to'liq qo'shiq (vokal+musiqa) yaratadi (15 coin)\n"
        "💰 Balans — coin miqdoringizni ko'rsatadi\n⚙️ Sozlamalar — bot haqida ma'lumot\n\n"
        "Oddiy savolni yozsangiz, sun'iy intellekt sizga javob beradi (1 coin).",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"⚙️ *Sozlamalar*\n\nMatn modeli: `{MODEL_NAME}`\nRasm modeli: `{IMAGE_MODEL_NAME}`\n"
        f"Video modellari: Wan 2.6, Kling 1.6\nOvoz modeli: `{TTS_MODEL_NAME}`\n",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    awaiting_image_prompt[chat_id] = False
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt.pop(chat_id, None)
    awaiting_voice_text[chat_id] = False
    await update.message.reply_text("🆕 Yangi suhbat boshlandi. Nima haqida gaplashamiz?", reply_markup=main_menu_keyboard())


async def ask_image_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_IMAGE:
        await update.message.reply_text(f"❌ Coin yetarli emas. Rasm uchun {COIN_COST_IMAGE} coin kerak, sizda {get_balance(chat_id)} coin bor.")
        return
    awaiting_image_prompt[chat_id] = True
    await update.message.reply_text(
        "🎨 Qanday rasm chizishimni xohlaysiz? Tavsiflab yozing.\nMasalan: _qor bosgan tog' manzarasi, quyosh botishi_",
        parse_mode="Markdown",
    )


async def ask_video_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_VIDEO:
        await update.message.reply_text(f"❌ Coin yetarli emas. Video uchun {COIN_COST_VIDEO} coin kerak, sizda {get_balance(chat_id)} coin bor.")
        return
    awaiting_video_model_choice[chat_id] = True
    await update.message.reply_text(
        "🎬 Qaysi model bilan video yaratamiz?\n\n🟢 Wan 2.6 — tezroq va arzonroq (~5 soniya)\n🔵 Kling 1.6 — sifatliroq (~10 soniya), biroz qimmatroq",
        reply_markup=video_model_keyboard(),
    )


async def ask_video_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, model_key: str):
    chat_id = update.effective_chat.id
    awaiting_video_model_choice[chat_id] = False
    awaiting_video_prompt[chat_id] = model_key
    await update.message.reply_text(
        "✏️ Endi video uchun tavsif yozing.\nMasalan: _dengiz bo'yida quyosh botishi, to'lqinlar sohilga urilmoqda_",
        parse_mode="Markdown",
    )


async def ask_voice_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_VOICE:
        await update.message.reply_text(f"❌ Coin yetarli emas. Ovozga aylantirish uchun {COIN_COST_VOICE} coin kerak, sizda {get_balance(chat_id)} coin bor.")
        return
    awaiting_voice_text[chat_id] = True
    await update.message.reply_text(
        "🔊 Qaysi matnni ovozga aylantirishim kerak? Matnni yozing.\n"
        "Masalan: _Assalomu alaykum, bugun ob-havo juda yaxshi_",
        parse_mode="Markdown",
    )


async def generate_voice_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_VOICE:
        await update.message.reply_text(f"❌ Coin yetarli emas. {COIN_COST_VOICE} coin kerak.", reply_markup=main_menu_keyboard())
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    await update.message.reply_text("🔊 Ovoz yaratilmoqda, biroz kuting...")

    try:
        def run_tts():
            return openai_client.audio.speech.create(
                model=TTS_MODEL_NAME,
                voice=TTS_VOICE,
                input=text,
            )

        response = await asyncio.to_thread(run_tts)
        audio_path = f"/tmp/voice_{chat_id}.mp3"
        response.stream_to_file(audio_path)

        new_balance = change_balance(chat_id, -COIN_COST_VOICE)
        with open(audio_path, "rb") as audio_file:
            await update.message.reply_voice(
                voice=audio_file,
                caption=f"🔊 -{COIN_COST_VOICE} coin (qoldi: {new_balance})",
                reply_markup=main_menu_keyboard(),
            )
        os.remove(audio_path)
    except Exception as e:
        logger.error(f"OpenAI TTS xatosi: {e}")
        await update.message.reply_text(
            "Kechirasiz, ovoz yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard(),
        )


async def ask_music_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_MUSIC:
        await update.message.reply_text(f"❌ Coin yetarli emas. Qo'shiq uchun {COIN_COST_MUSIC} coin kerak, sizda {get_balance(chat_id)} coin bor.")
        return
    awaiting_music_prompt[chat_id] = True
    await update.message.reply_text(
        "🎵 Qanday qo'shiq yarataylik? Mavzu, kayfiyat va janrni yozing.\n"
        "Masalan: _sevgi haqida quvnoq pop qo'shiq_ yoki lirika matnini ham yozishingiz mumkin.",
        parse_mode="Markdown",
    )


async def generate_music_from_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_MUSIC:
        await update.message.reply_text(f"❌ Coin yetarli emas. Qo'shiq uchun {COIN_COST_MUSIC} coin kerak.", reply_markup=main_menu_keyboard())
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    await update.message.reply_text("🎵 Qo'shiq yaratilmoqda, bu bir necha daqiqa vaqt olishi mumkin...")

    try:
        def run_generation():
            return fal_client.subscribe(MUSIC_MODEL_ID, arguments={"prompt": prompt})

        result = await asyncio.to_thread(run_generation)

        audio_url = None
        if isinstance(result, dict):
            if "audio" in result and isinstance(result["audio"], dict):
                audio_url = result["audio"].get("url")
            elif "audio_url" in result:
                audio_url = result["audio_url"]

        if not audio_url:
            raise ValueError(f"Audio URL topilmadi. Natija: {result}")

        new_balance = change_balance(chat_id, -COIN_COST_MUSIC)
        await update.message.reply_audio(
            audio=audio_url,
            caption=f"🎵 {prompt}\n\n🪙 -{COIN_COST_MUSIC} coin (qoldi: {new_balance})",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"fal.ai qo'shiq yaratish xatosi: {e}")
        await update.message.reply_text(
            "Kechirasiz, qo'shiq yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard(),
        )


async def generate_video_from_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str, model_key: str):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_VIDEO:
        await update.message.reply_text(f"❌ Coin yetarli emas. Video uchun {COIN_COST_VIDEO} coin kerak.", reply_markup=main_menu_keyboard())
        return
    model_info = VIDEO_MODELS[model_key]
    await context.bot.send_chat_action(chat_id=chat_id, action="record_video")
    await update.message.reply_text(
        f"🎬 {model_info['label']} orqali video yaratilmoqda...\nBu bir necha daqiqa vaqt olishi mumkin, iltimos kuting.",
        reply_markup=main_menu_keyboard(),
    )
    try:
        def run_generation():
            return fal_client.subscribe(model_info["model_id"], arguments={"prompt": prompt})
        result = await asyncio.to_thread(run_generation)
        video_url = None
        if isinstance(result, dict):
            if "video" in result and isinstance(result["video"], dict):
                video_url = result["video"].get("url")
            elif "video_url" in result:
                video_url = result["video_url"]
        if not video_url:
            raise ValueError(f"Video URL topilmadi. Natija: {result}")
        new_balance = change_balance(chat_id, -COIN_COST_VIDEO)
        await context.bot.send_chat_action(chat_id=chat_id, action="upload_video")
        await update.message.reply_video(
            video=video_url,
            caption=f"🎬 {prompt}\n\n🪙 -{COIN_COST_VIDEO} coin (qoldi: {new_balance})",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"fal.ai video yaratish xatosi: {e}")
        await update.message.reply_text(
            "Kechirasiz, video yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard(),
        )


async def generate_image_from_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    chat_id = update.effective_chat.id
    if get_balance(chat_id) < COIN_COST_IMAGE:
        await update.message.reply_text(f"❌ Coin yetarli emas. Rasm uchun {COIN_COST_IMAGE} coin kerak.", reply_markup=main_menu_keyboard())
        return
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    await update.message.reply_text("🎨 Rasm yaratilmoqda, biroz kuting...")
    try:
        result = openai_client.images.generate(model=IMAGE_MODEL_NAME, prompt=prompt, size="1024x1024", quality="standard", n=1)
        image_url = result.data[0].url
        new_balance = change_balance(chat_id, -COIN_COST_IMAGE)
        await update.message.reply_photo(
            photo=image_url,
            caption=f"🖼 {prompt}\n\n🪙 -{COIN_COST_IMAGE} coin (qoldi: {new_balance})",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"OpenAI rasm yaratish xatosi: {e}")
        await update.message.reply_text(
            "Kechirasiz, rasm yaratishda xatolik yuz berdi. Coin yechilmadi. Birozdan so'ng qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard(),
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if user_text == BTN_NEW_CHAT:
        await new_chat(update, context)
        return
    if user_text == BTN_IMAGE:
        await ask_image_prompt(update, context)
        return
    if user_text == BTN_VIDEO:
        await ask_video_model(update, context)
        return
    if user_text == BTN_VOICE:
        await ask_voice_text(update, context)
        return
    if user_text == BTN_MUSIC:
        await ask_music_prompt(update, context)
        return
    if user_text == BTN_BALANCE:
        await show_balance(update, context)
        return
    if user_text == BTN_SETTINGS:
        await settings_command(update, context)
        return
    if user_text == BTN_HELP:
        await help_command(update, context)
        return

    if awaiting_video_model_choice.get(chat_id):
        if user_text == BTN_VIDEO_WAN:
            await ask_video_prompt(update, context, "wan")
            return
        elif user_text == BTN_VIDEO_KLING:
            await ask_video_prompt(update, context, "kling")
            return
        else:
            await update.message.reply_text("Iltimos, pastdagi tugmalardan birini tanlang.", reply_markup=video_model_keyboard())
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

    if get_balance(chat_id) < COIN_COST_TEXT:
        await update.message.reply_text(f"❌ Coin yetarli emas. Xabar yuborish uchun {COIN_COST_TEXT} coin kerak.", reply_markup=main_menu_keyboard())
        return

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    history = conversation_history[chat_id]
    history.append({"role": "user", "content": user_text})
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = claude_client.messages.create(model=MODEL_NAME, max_tokens=1024, system=SYSTEM_PROMPT, messages=history)
        reply_text = "".join(block.text for block in response.content if block.type == "text")
    except Exception as e:
        logger.error(f"Anthropic API xatosi: {e}")
        reply_text = "Kechirasiz, javob berishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
        conversation_history[chat_id] = history
        await update.message.reply_text(reply_text, reply_markup=main_menu_keyboard())
        return

    history.append({"role": "assistant", "content": reply_text})
    conversation_history[chat_id] = history
    new_balance = change_balance(chat_id, -COIN_COST_TEXT)
    await update.message.reply_text(reply_text, reply_markup=main_menu_keyboard())


def main():
    missing = []
    if "BU_YERGA" in TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if "BU_YERGA" in ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if "BU_YERGA" in OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if "BU_YERGA" in FAL_KEY:
        missing.append("FAL_KEY")
    if "BU_YERGA" in ADMIN_ID:
        missing.append("ADMIN_ID")

    if missing:
        print(f"\n⚠️  DIQQAT: Quyidagi kalitlar sozlanmagan: {', '.join(missing)}\n")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", new_chat))
    app.add_handler(CommandHandler("id", show_id))
    app.add_handler(CommandHandler("balance", show_balance))
    app.add_handler(CommandHandler("coin_qoshish", add_coins_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
