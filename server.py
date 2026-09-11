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
import traceback
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
    generate_fal_image,
    generate_fal_music,
    generate_fal_video,
    generate_higgsfield_image,
    get_balance,
    get_lang,
)
from i18n import DEFAULT_LANGUAGE, style_label, t

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
# ADMIN'GA XATOLIK YUBORISH (DIAGNOSTIKA)
# ============================================================
#
# bot.py'dagi notify_admin_error bilan bir xil maqsadda —
# lekin bu yerda `context` yo'q, shuning uchun to'g'ridan-to'g'ri
# telegram_application.bot orqali yuboradi (pastda aniqlanadi).

async def notify_admin_error_miniapp(title: str):

    if not ADMIN_ID or "BU_YERGA" in ADMIN_ID:
        return

    if telegram_application is None:
        return

    tb_text = traceback.format_exc()

    if len(tb_text) > 3500:
        tb_text = "...\n" + tb_text[-3500:]

    try:

        await telegram_application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=(
                f"🔴 XATOLIK (Mini App): {title}\n\n"
                f"```\n{tb_text}\n```"
            ),
            parse_mode="Markdown",
        )

    except Exception as notify_exc:

        logger.warning(
            "Admin'ga xatolik xabarini "
            f"yuborib bo'lmadi: {notify_exc}"
        )


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
async def api_list_styles(
    lang: str = DEFAULT_LANGUAGE,
):

    return [
        {
            "id": key,
            "label": style_label(key, lang),
        }
        for key in STYLE_TEMPLATES.keys()
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


@api.get("/api/lang")
async def api_get_lang(init_data: str):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    return {
        "lang": get_lang(chat_id)
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

    lang = get_lang(chat_id)

    if style_id not in STYLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=t(lang, "unknown_style"),
        )

    if get_balance(chat_id) < COIN_COST_STYLE:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_STYLE,
                balance=get_balance(chat_id),
            ),
        )

    if photo is None:
        raise HTTPException(
            status_code=400,
            detail=t(lang, "photo_missing"),
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

    except Exception:

        # MUHIM: logger.exception to'liq traceback'ni
        # Railway logiga yozadi (avval faqat "{e}" — bitta
        # qator — yozilardi). Qo'shimcha ravishda shu
        # traceback to'g'ridan-to'g'ri admin'ga Telegram
        # xabari sifatida yuboriladi.

        logger.exception(
            f"Mini App stil xatosi ({style_id}):"
        )

        await notify_admin_error_miniapp(
            f"Stil qo'llash — {style_id}"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "style_error"),
        )

    if not result_url:
        raise HTTPException(
            status_code=500,
            detail=t(lang, "no_result"),
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
                    f"🖼 {style_label(style_id, lang)}\n\n"
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

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_TEXT:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_TEXT,
                balance=get_balance(chat_id),
            ),
        )

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

    except Exception:

        logger.exception(
            "Mini App chat xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App chat"
        )

        conversation_history[chat_id] = history

        raise HTTPException(
            status_code=500,
            detail=t(lang, "text_error"),
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
):

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_IMAGE:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_IMAGE,
                balance=get_balance(chat_id),
            ),
        )

    try:

        image_url = await generate_fal_image(
            prompt,
            aspect_ratio=aspect_ratio,
        )

    except Exception:

        logger.exception(
            "Mini App rasm xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App rasm yaratish"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "image_error"),
        )

    if not image_url:
        raise HTTPException(
            status_code=500,
            detail=t(lang, "no_result"),
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

    lang = get_lang(chat_id)

    if model_key not in VIDEO_MODELS:
        raise HTTPException(
            status_code=400,
            detail=t(lang, "unknown_video_model"),
        )

    if get_balance(chat_id) < COIN_COST_VIDEO:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VIDEO,
                balance=get_balance(chat_id),
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

    except Exception:

        logger.exception(
            "Mini App video xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App video yaratish"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "video_error"),
        )

    if not video_url:
        raise HTTPException(
            status_code=500,
            detail=t(lang, "no_result"),
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

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_MUSIC:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_MUSIC,
                balance=get_balance(chat_id),
            ),
        )

    try:

        audio_url = await generate_fal_music(
            prompt
        )

    except Exception:

        logger.exception(
            "Mini App musiqa xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App musiqa yaratish"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "music_error"),
        )

    if not audio_url:
        raise HTTPException(
            status_code=500,
            detail=t(lang, "no_result"),
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

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_VOICE:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VOICE,
                balance=get_balance(chat_id),
            ),
        )

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

    except Exception:

        logger.exception(
            "Mini App ovoz xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App ovoz yaratish"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "voice_error"),
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
            detail=t(lang, "no_result"),
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

    try:

        telegram_application = build_application()

        await telegram_application.initialize()
        await telegram_application.start()

        await telegram_application.updater.start_polling()

        logger.info(
            "🤖 MUBORAKXON bot (polling) va "
            "Mini App servera birga ishga tushdi."
        )

        # Jarayon tirik turishi uchun cheksiz kutish.
        # FastAPI/uvicorn HTTP so'rovlarini alohida
        # qabul qilaveradi.
        await asyncio.Event().wait()

    except Exception:

        # MUHIM: bu try/except bo'lmasa, bot ishga
        # tushishida xato chiqsa (masalan noto'g'ri token,
        # tarmoq xatosi va h.k.), bu xato hech qayerga
        # yozilmasdan "yutilib" ketardi — bot esa
        # javob bermay qolardi, Railway logida esa
        # hech narsa ko'rinmasdi.
        logger.exception(
            "🔴 Bot polling ishga tushirishda "
            "XATO — bot xabarlarga javob "
            "bermaydi:"
        )

        raise

    finally:

        if telegram_application is not None:
            await telegram_application.updater.stop()
            await telegram_application.stop()
            await telegram_application.shutdown()


# MUHIM: yaratilgan asyncio vazifasiga kuchli (doimiy)
# havola saqlanadi. Agar bu global o'zgaruvchida
# saqlanmasa, Python'ning chiqindi yig'uvchisi vazifani
# kutilmaganda to'xtatib qo'yishi mumkin edi — bu ham
# "bot sababsiz javob bermay qoladi" muammosining
# ehtimoliy manbai edi.
_bot_polling_task = None


def _on_bot_polling_done(task: asyncio.Task):
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "🔴 Bot polling vazifasi kutilmaganda "
            f"to'xtadi: {exc}"
        )


@api.on_event("startup")
async def on_startup():

    global _bot_polling_task

    _bot_polling_task = asyncio.create_task(
        run_bot_polling()
    )

    _bot_polling_task.add_done_callback(
        _on_bot_polling_done
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
