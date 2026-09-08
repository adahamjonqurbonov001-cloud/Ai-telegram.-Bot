"""
MUBORAKXON — Mini App serveri

Bu fayl ikkita narsani BITTA jarayonda birga ishga tushiradi:
    1) Telegram bot (bot.py'dagi barcha handlerlar, polling rejimida)
    2) Mini App uchun veb-server (FastAPI) — webapp/ papkasidagi
       sahifani va /api/* endpointlarini beradi

Railway'da ishga tushirish uchun start buyrug'ini shunga o'zgartiring:
    python server.py
(avvalgi "python bot.py" o'rniga)

Railway avtomatik $PORT muhit o'zgaruvchisini beradi — server
o'sha portda tinglaydi.

MUHIM — MINI APP'NI TELEGRAM'DA ULASH:
    1) @BotFather'ga o'ting → /mybots → botingizni tanlang
       → Bot Settings → Menu Button → Configure Menu Button
       → URL sifatida Railway bergan domenni kiriting
         (masalan: https://sizning-loyiha.up.railway.app)
    2) Shundan keyin foydalanuvchilar chat pastidagi
       menyu tugmasidan Mini App'ni ochishlari mumkin bo'ladi.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from urllib.parse import parse_qsl

import edge_tts
import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from bot import (
    ADMIN_ID,
    COIN_COST_IMAGE,
    COIN_COST_MUSIC,
    COIN_COST_STYLE,
    COIN_COST_TEXT,
    COIN_COST_VIDEO,
    COIN_COST_VOICE,
    DEFAULT_TTS_VOICE,
    MAX_HISTORY_MESSAGES,
    MODEL_NAME,
    STYLE_TEMPLATES,
    SYSTEM_PROMPT,
    TELEGRAM_BOT_TOKEN,
    TTS_VOICE_MAP,
    VIDEO_MODELS,
    apply_fal_ai_style,
    build_application,
    change_balance,
    claude_client,
    conversation_history,
    generate_fal_music,
    generate_fal_video,
    generate_higgsfield_image,
    get_balance,
    get_lang,
)

# Mini App'da til nomlarini Claude'ga aytish uchun (bot.py'dagi
# handle_message ichidagi xuddi shu lug'at bilan bir xil).
LANG_NAMES = {
    "uz": "o'zbek",
    "ru": "русском",
    "kk": "қазақ",
    "tg": "тоҷикӣ",
    "ky": "кыргыз",
    "en": "English",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# TELEGRAM initData TEKSHIRUVI
# ============================================================
#
# MUHIM: Mini App frontendidan (app.js) kelgan har bir so'rov
# o'zi bilan Telegram bergan "initData" satrini olib keladi.
# Bu satr Telegram tomonidan HMAC-SHA256 bilan imzolangan.
# Agar bu imzoni TEKSHIRMASAK, istalgan odam o'zining
# chat_id'ini soxtalashtirib, boshqa birovning coin balansidan
# bepul foydalanishi mumkin bo'lardi. Shu sababli har bir
# so'rovda bu funksiya chaqiriladi.
# Rasmiy algoritm:
# https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app


def verify_telegram_init_data(init_data: str) -> dict:

    if not init_data:
        raise HTTPException(
            status_code=401,
            detail="initData topilmadi — Mini App Telegram "
            "ichida ochilmagan bo'lishi mumkin.",
        )

    try:
        parsed = dict(
            parse_qsl(
                init_data,
                strict_parsing=True,
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="initData noto'g'ri formatda",
        )

    received_hash = parsed.pop(
        "hash",
        None,
    )

    if not received_hash:
        raise HTTPException(
            status_code=400,
            detail="initData'da hash topilmadi",
        )

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(
            parsed.items()
        )
    )

    secret_key = hmac.new(
        b"WebAppData",
        TELEGRAM_BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        computed_hash,
        received_hash,
    ):
        raise HTTPException(
            status_code=403,
            detail="initData imzosi noto'g'ri — "
            "so'rov ishonchli emas",
        )

    auth_date = int(
        parsed.get(
            "auth_date",
            "0",
        )
    )

    # 24 soatdan eski initData qabul qilinmaydi
    if time.time() - auth_date > 86400:
        raise HTTPException(
            status_code=403,
            detail="initData eskirgan, Mini App'ni "
            "qayta oching",
        )

    user_raw = parsed.get("user")

    if not user_raw:
        raise HTTPException(
            status_code=400,
            detail="foydalanuvchi ma'lumoti topilmadi",
        )

    return json.loads(user_raw)


# ============================================================
# FASTAPI ILOVASI
# ============================================================

api = FastAPI(title="MUBORAKXON Mini App")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bot ishga tushgach shu global o'zgaruvchiga yoziladi —
# shunda /api/apply-style natijani to'g'ridan-to'g'ri
# foydalanuvchi chatiga yubora oladi.
telegram_application = None


@api.post("/api/new-chat")
async def api_new_chat(
    init_data: str = Form(...),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    conversation_history[chat_id] = []

    return {"ok": True}


@api.get("/api/styles")
async def api_list_styles():

    return [
        {
            "id": key,
            "label": info["label"],
        }
        for key, info in STYLE_TEMPLATES.items()
    ]


@api.get("/api/balance")
async def api_get_balance(init_data: str):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    return {
        "balance": get_balance(chat_id)
    }


@api.post("/api/apply-style")
async def api_apply_style(
    init_data: str = Form(...),
    style_id: str = Form(...),
    photo: UploadFile = None,
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if style_id not in STYLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail="Noma'lum stil",
        )

    if get_balance(chat_id) < COIN_COST_STYLE:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_STYLE})"
            ),
        )

    if photo is None:
        raise HTTPException(
            status_code=400,
            detail="Rasm yuborilmadi",
        )

    image_bytes = await photo.read()

    style_prompt = STYLE_TEMPLATES[
        style_id
    ]["prompt"]

    try:

        result_url = await apply_fal_ai_style(
            image_bytes,
            style_prompt,
        )

    except Exception as e:

        logger.error(
            f"Mini App stil xatosi: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Stil qo'llashda xatolik "
            "yuz berdi, qayta urinib ko'ring",
        )

    if not result_url:
        raise HTTPException(
            status_code=500,
            detail="Natija olinmadi, "
            "qayta urinib ko'ring",
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_STYLE,
    )

    # Natijani foydalanuvchi chatiga ham yuboramiz —
    # shunda Mini App yopilsa ham natija yo'qolmaydi.
    if telegram_application is not None:

        try:

            await telegram_application.bot.send_photo(
                chat_id=chat_id,
                photo=result_url,
                caption=(
                    f"🖼 {STYLE_TEMPLATES[style_id]['label']}\n\n"
                    f"🪙 -{COIN_COST_STYLE} coin "
                    f"({new_balance})"
                ),
            )

        except Exception as e:

            # Chatga yuborib bo'lmasa ham, Mini App natijani
            # o'zida ko'rsatadi — foydalanuvchi baribir
            # natijani ko'radi.
            logger.warning(
                "Natijani chatga yuborib "
                f"bo'lmadi: {e}"
            )

    return {
        "result_url": result_url,
        "balance": new_balance,
    }


@api.post("/api/chat")
async def api_chat(
    init_data: str = Form(...),
    message: str = Form(...),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if get_balance(chat_id) < COIN_COST_TEXT:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_TEXT})"
            ),
        )

    lang = get_lang(chat_id)

    history = conversation_history.get(
        chat_id,
        [],
    )

    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[
            -MAX_HISTORY_MESSAGES:
        ]

    lang_name = LANG_NAMES.get(
        lang,
        "o'zbek",
    )

    dynamic_system_prompt = (
        SYSTEM_PROMPT
        + f" Javobingizni {lang_name} "
        "tilida yozing."
    )

    try:

        response = claude_client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system=dynamic_system_prompt,
            messages=history,
        )

        reply_text = "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

    except Exception as e:

        logger.error(
            f"Mini App chat xatosi: {e}"
        )

        conversation_history[chat_id] = history

        raise HTTPException(
            status_code=500,
            detail="Claude bilan bog'lanishda "
            "xatolik",
        )

    history.append(
        {
            "role": "assistant",
            "content": reply_text,
        }
    )

    conversation_history[chat_id] = history

    new_balance = change_balance(
        chat_id,
        -COIN_COST_TEXT,
    )

    return {
        "reply": reply_text,
        "balance": new_balance,
    }


@api.post("/api/generate-image")
async def api_generate_image(
    init_data: str = Form(...),
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    resolution: str = Form("720p"),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if get_balance(chat_id) < COIN_COST_IMAGE:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_IMAGE})"
            ),
        )

    try:

        image_url = await generate_higgsfield_image(
            prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

    except Exception as e:

        logger.error(
            f"Mini App rasm xatosi: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Rasm yaratishda xatolik",
        )

    if not image_url:
        raise HTTPException(
            status_code=500,
            detail="Rasm yaratilmadi, "
            "qayta urinib ko'ring",
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_IMAGE,
    )

    return {
        "image_url": image_url,
        "balance": new_balance,
    }


@api.post("/api/generate-video")
async def api_generate_video(
    init_data: str = Form(...),
    prompt: str = Form(...),
    model_key: str = Form("wan"),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if model_key not in VIDEO_MODELS:
        raise HTTPException(
            status_code=400,
            detail="Noma'lum video model",
        )

    if get_balance(chat_id) < COIN_COST_VIDEO:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_VIDEO})"
            ),
        )

    model_id = VIDEO_MODELS[model_key][
        "model_id"
    ]

    try:

        video_url = await generate_fal_video(
            prompt,
            model_id,
        )

    except Exception as e:

        logger.error(
            f"Mini App video xatosi: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Video yaratishda xatolik",
        )

    if not video_url:
        raise HTTPException(
            status_code=500,
            detail="Video yaratilmadi, "
            "qayta urinib ko'ring",
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_VIDEO,
    )

    return {
        "video_url": video_url,
        "balance": new_balance,
    }


@api.post("/api/generate-music")
async def api_generate_music(
    init_data: str = Form(...),
    prompt: str = Form(...),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if get_balance(chat_id) < COIN_COST_MUSIC:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_MUSIC})"
            ),
        )

    try:

        audio_url = await generate_fal_music(
            prompt
        )

    except Exception as e:

        logger.error(
            f"Mini App musiqa xatosi: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Musiqa yaratishda xatolik",
        )

    if not audio_url:
        raise HTTPException(
            status_code=500,
            detail="Musiqa yaratilmadi, "
            "qayta urinib ko'ring",
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_MUSIC,
    )

    return {
        "audio_url": audio_url,
        "balance": new_balance,
    }


@api.post("/api/generate-voice")
async def api_generate_voice(
    init_data: str = Form(...),
    text: str = Form(...),
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    if get_balance(chat_id) < COIN_COST_VOICE:
        raise HTTPException(
            status_code=402,
            detail=(
                "Coin yetarli emas "
                f"(kerak: {COIN_COST_VOICE})"
            ),
        )

    lang = get_lang(chat_id)

    selected_voice = TTS_VOICE_MAP.get(
        lang,
        DEFAULT_TTS_VOICE,
    )

    audio_path = (
        f"/tmp/miniapp_voice_"
        f"{chat_id}_{int(time.time())}.mp3"
    )

    audio_bytes = None

    try:

        communicate = edge_tts.Communicate(
            text,
            selected_voice,
        )

        await communicate.save(
            audio_path
        )

        with open(
            audio_path,
            "rb",
        ) as f:
            audio_bytes = f.read()

    except Exception as e:

        logger.error(
            f"Mini App ovoz xatosi: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Ovoz yaratishda xatolik",
        )

    finally:

        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

    if not audio_bytes:
        raise HTTPException(
            status_code=500,
            detail="Ovoz yaratilmadi",
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_VOICE,
    )

    return {
        "audio_base64": base64.b64encode(
            audio_bytes
        ).decode("ascii"),
        "balance": new_balance,
    }


# Mini App statik fayllari (index.html, style.css, app.js) —
# BARCHA yuqoridagi /api/* yo'llaridan KEYIN ro'yxatdan
# o'tkazilishi shart, aks holda ular ustidan yozib yuboradi.
WEBAPP_DIR = os.path.join(
    os.path.dirname(__file__),
    "webapp",
)

api.mount(
    "/",
    StaticFiles(
        directory=WEBAPP_DIR,
        html=True,
    ),
    name="webapp",
)


# ============================================================
# BOT'NI FASTAPI BILAN BIRGA ISHGA TUSHIRISH
# ============================================================


async def run_bot_polling():
    """
    bot.py'dagi Application'ni FastAPI bilan bir xil asyncio
    tsiklida polling rejimida ishga tushiradi.
    """

    global telegram_application

    telegram_application = build_application()

    await telegram_application.initialize()
    await telegram_application.start()

    await telegram_application.updater.start_polling()

    logger.info(
        "🤖 MUBORAKXON bot (polling) va "
        "Mini App servera birga ishga tushdi."
    )

    # Jarayon tirik turishi uchun cheksiz kutish.
    # FastAPI/uvicorn HTTP so'rovlarini alohida qabul qilaveradi.
    try:
        await asyncio.Event().wait()
    finally:
        await telegram_application.updater.stop()
        await telegram_application.stop()
        await telegram_application.shutdown()


@api.on_event("startup")
async def on_startup():
    asyncio.create_task(
        run_bot_polling()
    )


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "8000",
        )
    )

    uvicorn.run(
        api,
        host="0.0.0.0",
        port=port,
    )
