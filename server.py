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
import re
import logging
import os
import time
import traceback
import uuid
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
    COIN_COST_VIDEO_IMAGE_EXTRA,
    COIN_COST_VIDEO_PRO_EXTRA,
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

async def notify_admin_error_miniapp(title: str):

    if not ADMIN_ID or "BU_YERGA" in ADMIN_ID:
        return

    if telegram_application is None:
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

        await telegram_application.bot.send_message(
            chat_id=int(ADMIN_ID),
            text=(
                f"🔴 XATOLIK (Mini App): {title}\n\n"
                f"{tb_text}"
            ),
        )

    except Exception as notify_exc:

        logger.warning(
            "Admin'ga xatolik xabarini "
            f"yuborib bo'lmadi: {notify_exc}"
        )


# ============================================================
# TELEGRAM initData TEKSHIRUVI
# ============================================================

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

telegram_application = None

# ============================================================
# VIDEO JOB HOLATI (asinxron generatsiya uchun)
# ============================================================
#
# MUHIM (YANGI): Kling video generatsiyasi 1-3+ daqiqa davom
# etishi mumkin. Avval /api/generate-video shu BUTUN vaqt
# davomida HTTP so'rovni ochiq ushlab turardi — mobil internet,
# Telegram WebView yoki Railway'ning oraliq proksisi shuncha
# uzoq ulanishni ochiq saqlay olmay, "Failed to fetch" xatosi
# bilan uzib qo'yardi (natija fal.ai'da tayyor bo'lsa ham,
# foydalanuvchi uni hech qachon ko'rmasdi).
#
# Endi /api/generate-video DARHOL (bir necha soniyada) job_id
# bilan javob qaytaradi, generatsiya esa orqa fonda
# (asyncio.create_task) davom etadi. Frontend esa
# /api/video-status?job_id=...ni har 3 soniyada so'rab turadi
# (polling) — bu naqadar uzoq davom etishidan qat'iy nazar
# ishonchli ishlaydi, chunki har bir alohida so'rov juda tez
# (bir necha millisekund) qaytadi.
#
# video_jobs — xotirada saqlanadigan oddiy lug'at. MUHIM: bu
# ham Railway fayl tizimi kabi vaqtinchalik — agar server qayta
# ishga tushsa (deploy, xatolik va h.k.), hali tugallanmagan
# job'lar yo'qoladi. Amaliyotda bu muammo emas, chunki bitta
# video generatsiyasi odatda bir necha daqiqada tugaydi va
# qayta deploy shu vaqt oralig'ida kamdan-kam bo'ladi.
video_jobs: dict[str, dict] = {}


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
            "thumbnail": STYLE_TEMPLATES[key].get(
                "thumbnail"
            ),
        }
        for key in STYLE_TEMPLATES.keys()
    ]


# ------------------------------------------------------------
# MUHIM (YANGI): Mini App'dagi video sozlamalari menyusi
# (model / format / davomiylik / rasmdan video) VIDEO_MODELS
# lug'atidan to'g'ridan-to'g'ri o'qiladi — shunda bot.py'da
# yangi model qo'shilsa, frontendni alohida yangilash shart
# bo'lmaydi (faqat shu ro'yxatdan chiqadi).
@api.get("/api/video-models")
async def api_list_video_models(
    lang: str = DEFAULT_LANGUAGE,
):

    return [
        {
            "key": key,
            "label": info["label"],
            "durations": info.get("durations"),
            "aspect_ratios": info.get("aspect_ratios"),
            "supports_image": bool(
                info.get("image_model_id")
            ),
            "extra_cost": (
                COIN_COST_VIDEO_PRO_EXTRA
                if key == "kling_pro"
                else 0
            ),
        }
        for key, info in VIDEO_MODELS.items()
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


async def run_video_generation_job(
    job_id: str,
    chat_id: int,
    lang: str,
    prompt: str,
    model_key: str,
    aspect_ratio: str | None,
    duration: str | None,
    image_bytes: bytes | None,
    total_cost: int,
):
    """
    MUHIM (YANGI): asosiy video generatsiyasi shu funksiyada,
    orqa fonda (HTTP so'rovdan mustaqil ravishda) bajariladi.
    Natija video_jobs[job_id]'ga yoziladi — frontend uni
    /api/video-status orqali so'rab oladi. Coin FAQAT
    muvaffaqiyatli yakunlangandan keyin yechiladi (xato bo'lsa
    hech narsa yechilmaydi — asl xulq-atvor saqlanib qolgan).
    """

    try:

        video_url = await generate_fal_video(
            prompt,
            model_key,
            aspect_ratio=aspect_ratio,
            duration=duration,
            image_bytes=image_bytes,
        )

    except Exception:

        logger.exception(
            "Mini App video xatosi (job):"
        )

        await notify_admin_error_miniapp(
            "Mini App video yaratish"
        )

        video_jobs[job_id] = {
            "status": "error",
            "detail": t(lang, "video_error"),
        }

        return

    if not video_url:

        video_jobs[job_id] = {
            "status": "error",
            "detail": t(lang, "no_result"),
        }

        return

    new_balance = change_balance(
        chat_id,
        -total_cost,
    )

    video_jobs[job_id] = {
        "status": "done",
        "video_url": video_url,
        "balance": new_balance,
        "cost": total_cost,
    }


@api.post("/api/generate-video")
async def api_generate_video(
    init_data: str = Form(...),
    prompt: str = Form(...),
    model_key: str = Form("wan"),
    aspect_ratio: str = Form(None),
    duration: str = Form(None),
    frame: UploadFile = None,
):
    """
    MUHIM (YANGI): endi bu endpoint videoni o'zi TAYYORLAMAYDI —
    faqat tekshiruvlarni (balans, model, rasm qo'llab-
    quvvatlanishi) o'tkazadi va orqa fon job'ini boshlab, DARHOL
    job_id bilan javob qaytaradi. Haqiqiy generatsiya
    run_video_generation_job'da davom etadi (yuqoriga qarang).
    Frontend natijani /api/video-status?job_id=... orqali
    so'rab-so'rab (polling) oladi.

    Qo'shimcha parametrlar avvalgidek:
        - aspect_ratio, duration — model qo'llab-quvvatlasa
        - frame — rasmdan video uchun boshlang'ich kadr

    Narx: "kling_pro" — +COIN_COST_VIDEO_PRO_EXTRA;
    rasmdan video — +COIN_COST_VIDEO_IMAGE_EXTRA. Coin FAQAT
    job muvaffaqiyatli tugagandan keyin yechiladi.
    """

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

    model_info = VIDEO_MODELS[model_key]

    image_bytes = None

    if frame is not None:

        if not model_info.get("image_model_id"):
            raise HTTPException(
                status_code=400,
                detail=t(lang, "video_image_not_supported"),
            )

        image_bytes = await frame.read()

    total_cost = COIN_COST_VIDEO

    if model_key == "kling_pro":
        total_cost += COIN_COST_VIDEO_PRO_EXTRA

    if image_bytes is not None:
        total_cost += COIN_COST_VIDEO_IMAGE_EXTRA

    if get_balance(chat_id) < total_cost:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=total_cost,
                balance=get_balance(chat_id),
            ),
        )

    job_id = uuid.uuid4().hex

    video_jobs[job_id] = {
        "status": "pending",
        "chat_id": chat_id,
    }

    asyncio.create_task(
        run_video_generation_job(
            job_id,
            chat_id,
            lang,
            prompt,
            model_key,
            aspect_ratio,
            duration,
            image_bytes,
            total_cost,
        )
    )

    return {
        "job_id": job_id,
        "cost": total_cost,
    }


@api.get("/api/video-status")
async def api_video_status(
    job_id: str,
    init_data: str,
):
    """
    Frontend shu endpointni /api/generate-video qaytargan
    job_id bilan har necha soniyada so'rab turadi. Javob:
        {"status": "pending"}                       — hali tayyor emas
        {"status": "done", "video_url": ..., "balance": ...}
        {"status": "error", "detail": "..."}
    """

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    job = video_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="job topilmadi",
        )

    # MUHIM: job faqat uni boshlagan foydalanuvchiga ko'rinadi —
    # aks holda job_id'ni bilgan istalgan kishi boshqa
    # birovning video natijasini ko'ra olardi.
    if job.get("chat_id") != chat_id:
        raise HTTPException(
            status_code=403,
            detail="ruxsat yo'q",
        )

    if job["status"] == "done":
        # Natija bir marta o'qilgach, xotirani bo'shatamiz —
        # video_jobs cheksiz o'sib ketmasligi uchun.
        video_jobs.pop(job_id, None)

    elif job["status"] == "error":
        video_jobs.pop(job_id, None)

    return job


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


# MUHIM (YANGI): Telegram Mini App'ning ichki WebView'i (ayniqsa
# Android'da) index.html/app.js/style.css'ni juda "yopishqoq"
# keshlaydi — hatto Mini App'ni to'liq yopib qayta ochganda ham
# eski versiya ko'rsatilishi mumkin edi. Standart StaticFiles
# hech qanday Cache-Control header qo'ymaydi, shuning uchun
# brauzer o'zicha (heuristik) keshlashga qaror qilardi. Endi har
# bir statik fayl "hech qachon keshlama, har doim qayta tekshir"
# degan header bilan yuboriladi — shunda kelajakda fayl
# yangilansa, foydalanuvchi Mini App'ni qayta ochganda darhol
# eng so'nggi versiyani ko'radi.
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


api.mount(
    "/",
    NoCacheStaticFiles(
        directory=WEBAPP_DIR,
        html=True,
    ),
    name="webapp",
)


# ============================================================
# BOT'NI FASTAPI BILAN BIRGA ISHGA TUSHIRISH
# ============================================================


async def run_bot_polling():

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

        await asyncio.Event().wait()

    except Exception:

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
