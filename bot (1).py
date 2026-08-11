"""
Sun'iy Intellekt Telegram Bot
Claude (Anthropic) API orqali ishlaydi.

O'rnatish:
    pip install python-telegram-bot anthropic --upgrade

Ishga tushirish:
    python bot.py

Muhit o'zgaruvchilari (environment variables) orqali kalitlarni bering:
    TELEGRAM_BOT_TOKEN
    ANTHROPIC_API_KEY
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from anthropic import Anthropic

# ----------------------------------------------------------------------
# SOZLAMALAR (o'zingizga moslab o'zgartiring)
# ----------------------------------------------------------------------

# Kalitlarni to'g'ridan-to'g'ri shu yerga yozishingiz ham mumkin,
# lekin xavfsizlik uchun environment variable orqali berish tavsiya etiladi.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "BU_YERGA_TELEGRAM_TOKENINGIZNI_YOZING")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "BU_YERGA_ANTHROPIC_API_KEYINGIZNI_YOZING")

# Qaysi Claude modelidan foydalanish
MODEL_NAME = "claude-sonnet-4-6"

# Botning "shaxsiyati" - xohlasangiz o'zgartiring
SYSTEM_PROMPT = (
    "Sen foydali, samimiy va bilimdon sun'iy intellekt yordamchisisan. "
    "Foydalanuvchi bilan o'zbek tilida (agar u boshqa tilda yozmasa) muloqot qilasan. "
    "Javoblaring aniq, tushunarli va foydali bo'lsin."
)

# Har bir foydalanuvchi uchun necha xabar tarixini eslab qolish
MAX_HISTORY_MESSAGES = 20

# ----------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Har bir chat_id uchun suhbat tarixini xotirada saqlaymiz
# Eslatma: bot qayta ishga tushsa, tarix o'chib ketadi.
# Doimiy saqlash kerak bo'lsa, buni fayl yoki bazaga yozish kerak.
conversation_history: dict[int, list[dict]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text(
        "Salom! Men sun'iy intellekt asosida ishlaydigan botman. \n\n"
        "Menga istalgan savolingizni yozing — javob beraman.\n"
        "Suhbatni tozalash uchun /clear buyrug'ini yuboring."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("Suhbat tarixi tozalandi. ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    history = conversation_history[chat_id]
    history.append({"role": "user", "content": user_text})

    # Tarixni juda uzun bo'lib ketmasligi uchun kesib turamiz
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]

    # "yozmoqda..." holatini ko'rsatish
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        reply_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
    except Exception as e:
        logger.error(f"Anthropic API xatosi: {e}")
        reply_text = (
            "Kechirasiz, javob berishda xatolik yuz berdi. "
            "Birozdan so'ng qayta urinib ko'ring."
        )
        conversation_history[chat_id] = history  # xato bo'lsa ham tarixni saqlaymiz
        await update.message.reply_text(reply_text)
        return

    history.append({"role": "assistant", "content": reply_text})
    conversation_history[chat_id] = history

    await update.message.reply_text(reply_text)


def main():
    if "BU_YERGA" in TELEGRAM_BOT_TOKEN or "BU_YERGA" in ANTHROPIC_API_KEY:
        print(
            "\n⚠️  DIQQAT: Kalitlar sozlanmagan!\n"
            "bot.py faylida TELEGRAM_BOT_TOKEN va ANTHROPIC_API_KEY qiymatlarini "
            "to'g'ri qiymatlarga almashtiring, yoki environment variable sifatida bering.\n"
        )
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
