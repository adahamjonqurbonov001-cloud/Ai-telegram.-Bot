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
import httpx
import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot import (
    ADMIN_ID,
    COIN_COST_IMAGE,
    COIN_COST_MUSIC,
    COIN_COST_STYLE,
    COIN_COST_TEXT,
    COIN_COST_VIDEO,
    COIN_COST_VIDEO_ANALYZE,
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
    classify_and_maybe_generate,
    conversation_history,
    analyze_video_with_claude,
    edit_image_with_instruction,
    extract_video_frames,
    generate_fal_image,
    generate_fal_music,
    generate_fal_video,
    generate_higgsfield_image,
    get_balance,
    get_lang,
    get_tts_voice,
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
    message: str = Form(""),
    photo: UploadFile = None,
):
    """
    MUHIM (YANGI): endi bu endpoint "Agent" xatti-harakatini
    qo'llab-quvvatladi — oddiy matn javobi o'rniga, agar
    Claude foydalanuvchi xabarida aniq rasm/musiqa/ovoz
    so'rovini aniqlasa, mos generatsiyani AVTOMATIK ishga
    tushiradi (classify_and_maybe_generate — bot.py'da,
    Telegram bilan bir xil funksiya). Javob shakli endi
    "kind" maydoni bilan farqlanadi: "text" / "image" /
    "music" / "voice".

    MUHIM (YANA YANGI): agar so'rovga "photo" biriktirilgan
    bo'lsa, Claude'ning tool-tanlash bosqichi UMUMAN
    o'tkazib yuboriladi — bu holatda niyat aniq (mavjud
    rasmni "message" matnidagi ko'rsatmaga ko'ra tahrirlash),
    shuning uchun to'g'ridan-to'g'ri edit_image_with_instruction
    chaqiriladi (xuddi "Tayyor stillar"dagi bilan bir xil
    fal.ai modeli, faqat tayyor shablon o'rniga erkin buyruq).
    """

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    lang = get_lang(chat_id)

    # --------------------------------------------------------
    # RASM BIRIKTIRILGAN BO'LSA — TAHRIRLASH YO'LI
    # --------------------------------------------------------
    if photo is not None:

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

        photo_bytes = await photo.read()

        edit_instruction = message.strip() or (
            "Enhance and improve this photo's overall quality "
            "while keeping everything else unchanged."
        )

        try:

            result_url = await edit_image_with_instruction(
                photo_bytes,
                edit_instruction,
            )

        except Exception:

            logger.exception(
                "Mini App rasm tahrirlash xatosi:"
            )

            await notify_admin_error_miniapp(
                "Mini App chat — rasm tahrirlash"
            )

            raise HTTPException(
                status_code=500,
                detail=t(lang, "image_edit_error"),
            )

        if not result_url:
            raise HTTPException(
                status_code=500,
                detail=t(lang, "no_result"),
            )

        history = conversation_history.get(
            chat_id, []
        )

        history.append(
            {
                "role": "user",
                "content": f"[Sent a photo] {edit_instruction}",
            }
        )

        history.append(
            {
                "role": "assistant",
                "content": f"[Edited the photo: {edit_instruction}]",
            }
        )

        conversation_history[chat_id] = history

        new_balance = change_balance(
            chat_id,
            -COIN_COST_STYLE,
        )

        return {
            "kind": "image",
            "image_url": result_url,
            "balance": new_balance,
        }

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

    result = await classify_and_maybe_generate(
        chat_id,
        message,
        lang,
        history,
    )

    if result["type"] == "error":

        logger.error(
            "Mini App agent xatosi "
            "(classify_and_maybe_generate "
            "'error' qaytardi)"
        )

        await notify_admin_error_miniapp(
            "Mini App chat (agent)"
        )

        conversation_history[chat_id] = history

        raise HTTPException(
            status_code=500,
            detail=t(lang, "text_error"),
        )

    if result["type"] == "insufficient_coins":

        # Foydalanuvchi xabari tarixda qoladi — coin to'ldirib,
        # qayta yozganda kontekst yo'qolmaydi.
        conversation_history[chat_id] = history

        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=result["cost"],
                balance=get_balance(chat_id),
            ),
        )

    if result["type"] == "text":

        history.append(
            {
                "role": "assistant",
                "content": result["text"],
            }
        )

        conversation_history[chat_id] = history

        new_balance = change_balance(
            chat_id,
            -result["cost"],
        )

        return {
            "kind": "text",
            "reply": result["text"],
            "balance": new_balance,
        }

    if result["type"] == "image":

        history.append(
            {
                "role": "assistant",
                "content": (
                    f"[Generated an image: {result['prompt']}]"
                ),
            }
        )

        conversation_history[chat_id] = history

        new_balance = change_balance(
            chat_id,
            -result["cost"],
        )

        return {
            "kind": "image",
            "image_url": result["url"],
            "balance": new_balance,
        }

    if result["type"] == "music":

        history.append(
            {
                "role": "assistant",
                "content": (
                    f"[Generated music: {result['prompt']}]"
                ),
            }
        )

        conversation_history[chat_id] = history

        new_balance = change_balance(
            chat_id,
            -result["cost"],
        )

        return {
            "kind": "music",
            "audio_url": result["url"],
            "balance": new_balance,
        }

    if result["type"] == "voice":

        history.append(
            {
                "role": "assistant",
                "content": (
                    f"[Generated voice for: {result['text']}]"
                ),
            }
        )

        conversation_history[chat_id] = history

        new_balance = change_balance(
            chat_id,
            -result["cost"],
        )

        audio_b64 = base64.b64encode(
            result["audio_bytes"]
        ).decode("ascii")

        return {
            "kind": "voice",
            "audio_base64": audio_b64,
            "balance": new_balance,
        }

    # Kutilmagan holat — amalda yuzaga kelmasligi kerak.
    conversation_history[chat_id] = history

    raise HTTPException(
        status_code=500,
        detail=t(lang, "text_error"),
    )


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


MEDIA_TMP_DIR = "/tmp/muborakxon_media"

# Video+ovoz qaysi modellarda ishlashi (foydalanuvchi tanlovi
# bo'yicha — faqat Kling va Kling Pro, sifatliroq natija uchun).
VOICEOVER_ALLOWED_MODELS = {"kling", "kling_pro"}

# Birlashtirilgan fayl necha soniyadan keyin o'chirilishi —
# Railway diski cheksiz to'lib ketmasligi uchun (foydalanuvchi
# odatda natijani darhol ko'radi/yuklab oladi).
MEDIA_CLEANUP_DELAY_SECONDS = 900  # 15 daqiqa


async def _delete_media_file_later(path: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    try:
        os.remove(path)
    except Exception:
        pass


async def build_video_with_voiceover(
    video_url: str,
    voice_text: str,
    lang: str,
    voice_gender: str,
    job_id: str,
) -> str:
    """
    MUHIM (YANGI): fal.ai'dan kelgan OVOZSIZ videoni yuklab
    oladi, edge-tts orqali (get_tts_voice — bot.py'da avval
    tayyorlangan) o'zbekcha/tanlangan tildagi nutq yaratadi va
    ffmpeg bilan ikkalasini birlashtiradi. Natija fayl yo'lini
    qaytaradi (URL emas — server o'zi /api/media orqali xizmat
    qiladi, pastga qarang).

    ESLATMA: ffmpeg konteynerga nixpacks.toml orqali alohida
    o'rnatilishi kerak — agar u topilmasa, bu funksiya xato
    beradi va chaqiruvchi kod (run_video_generation_job) buni
    ushlab, foydalanuvchiga baribir OVOZSIZ videoni yetkazadi
    (butun job muvaffaqiyatsiz bo'lib qolmaydi).
    """

    os.makedirs(MEDIA_TMP_DIR, exist_ok=True)

    raw_video_path = os.path.join(
        MEDIA_TMP_DIR, f"raw_{job_id}.mp4"
    )
    audio_path = os.path.join(
        MEDIA_TMP_DIR, f"voice_{job_id}.mp3"
    )
    merged_path = os.path.join(
        MEDIA_TMP_DIR, f"merged_{job_id}.mp4"
    )

    # 1. Ovozsiz videoni yuklab olamiz
    async with httpx.AsyncClient(timeout=120) as client:
        video_resp = await client.get(video_url)
        video_resp.raise_for_status()
        with open(raw_video_path, "wb") as f:
            f.write(video_resp.content)

    # 2. edge-tts orqali nutq yaratamiz
    selected_voice = get_tts_voice(lang, voice_gender)

    communicate = edge_tts.Communicate(
        voice_text,
        selected_voice,
    )

    await communicate.save(audio_path)

    if (
        not os.path.exists(audio_path)
        or os.path.getsize(audio_path) == 0
    ):
        raise RuntimeError(
            "edge-tts ovoz fayli yaratmadi"
        )

    # 3. ffmpeg bilan birlashtiramiz. "-shortest" ikkalasidan
    # qisqarog'iga moslaydi (video odatda 5-10s, nutq ham
    # taxminan shuncha bo'lishi kutiladi — MUHIM: agar nutq
    # videodan ANCHA uzunroq bo'lsa, u kesib tashlanadi; agar
    # qisqaroq bo'lsa, video ham nutq bilan birga tugaydi. Bu
    # birinchi versiya uchun yetarli — kelajakda video uzunligini
    # nutqqa moslab uzaytirish/qisqartirish qo'shilishi mumkin.
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        merged_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr_bytes = await process.communicate()

    for tmp_path in (raw_video_path, audio_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    if process.returncode != 0 or not os.path.exists(merged_path):
        error_text = stderr_bytes.decode(
            "utf-8", errors="ignore"
        )[-800:]
        raise RuntimeError(
            f"ffmpeg birlashtirish xatosi: {error_text}"
        )

    asyncio.create_task(
        _delete_media_file_later(
            merged_path,
            MEDIA_CLEANUP_DELAY_SECONDS,
        )
    )

    return merged_path


# ============================================================
# AI STUDIO — bitta jumladan ko'p sahnali reklama video
# ============================================================
#
# MUHIM (YANGI): foydalanuvchi qisqa brief yozadi (masalan
# "mahsulotim uchun reklama qil"), ixtiyoriy ravishda mahsulot
# rasmini qo'shadi. Claude shu asosda AI_STUDIO_SCENE_COUNT ta
# sahna (har biri: vizual tavsif + diktor matni) rejalashtiradi.
# Har bir sahna alohida video+ovoz sifatida yaratiladi (yuqoridagi
# build_video_with_voiceover funksiyasi qayta ishlatiladi), so'ng
# barchasi ffmpeg bilan bitta uzun videoga birlashtiriladi.
#
# Bu — butun loyihadagi eng uzoq davom etadigan amal (3 ta video
# ketma-ket yaratiladi, har biri 1-3 daqiqa) — shuning uchun
# video_jobs/polling infratuzilmasi qayta ishlatiladi, faqat
# qo'shimcha "progress" maydoni bilan (foydalanuvchi qaysi
# bosqichda ekanini ko'rishi uchun).

AI_STUDIO_SCENE_COUNT = 3
COIN_COST_AI_STUDIO = COIN_COST_VIDEO * AI_STUDIO_SCENE_COUNT


async def plan_ad_scenes(
    brief: str,
    lang: str,
    has_product_photo: bool,
) -> list[dict]:
    """
    Claude'dan brief asosida AI_STUDIO_SCENE_COUNT ta sahna
    (JSON ko'rinishida) so'raydi. Har bir sahna:
        {"visual_prompt": "...", "voice_text": "..."}
    """

    lang_name = LANG_NAMES.get(lang, "o'zbek")

    system_prompt = (
        "You are a professional advertising creative director and "
        "video prompt engineer. Given a short brief from a user, "
        f"design EXACTLY {AI_STUDIO_SCENE_COUNT} short video scenes "
        "(5 seconds each) that together form one compelling short "
        "advertisement with a clear narrative arc (hook, product/"
        "benefit, call to action).\n\n"
        "Respond with ONLY valid JSON, no markdown formatting, no "
        "explanation, in EXACTLY this shape:\n"
        '{"scenes": [{"visual_prompt": "...", "voice_text": "..."}, '
        '{"visual_prompt": "...", "voice_text": "..."}, '
        '{"visual_prompt": "...", "voice_text": "..."}]}\n\n'
        "Rules:\n"
        '- "visual_prompt" MUST be written in English: vivid, '
        "specific, optimized for an AI video generator (describe "
        "subject, action, camera movement, lighting, mood).\n"
        f'- "voice_text" MUST be written in {lang_name}: a short, '
        "natural spoken narration line (under 15 words) for that "
        "scene.\n"
    )

    if has_product_photo:
        system_prompt += (
            "- The user has provided a product photo that will be "
            "used as the STARTING FRAME of the FIRST scene only — "
            "write the first scene's visual_prompt so it makes sense "
            "as an animation that begins from a static product "
            "photo.\n"
        )

    response = await asyncio.to_thread(
        claude_client.messages.create,
        model=MODEL_NAME,
        max_tokens=800,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": brief,
            }
        ],
    )

    raw_text = "".join(
        block.text
        for block in response.content
        if block.type == "text"
    ).strip()

    # MUHIM: Claude ba'zan JSON'ni ```json ... ``` bilan o'rab
    # yuborishi mumkin — shuni tozalaymiz, aks holda json.loads
    # xato beradi.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    data = json.loads(raw_text)

    scenes = data.get("scenes")

    if not isinstance(scenes, list) or not scenes:
        raise ValueError(
            "Claude sahnalarni kutilgan JSON "
            "formatida qaytarmadi"
        )

    return scenes[:AI_STUDIO_SCENE_COUNT]


async def concat_video_clips(
    clip_paths: list[str],
    job_id: str,
) -> str:
    """
    Bir nechta lokal video faylni (har biri alohida sahna) ffmpeg
    "concat" demuxeri orqali BITTA videoga birlashtiradi. Avval
    tez ("-c copy") usul sinaladi — barcha kliplar bir xil
    kodek/formatda bo'lsa (odatda shunday, chunki hammasi bitta
    Kling modelidan keladi) darhol ishlaydi. Agar formatlar mos
    kelmasa, qayta kodlash (sekinroq, lekin ishonchli) bilan
    zaxira urinish qilinadi.
    """

    os.makedirs(MEDIA_TMP_DIR, exist_ok=True)

    list_file_path = os.path.join(
        MEDIA_TMP_DIR, f"concat_list_{job_id}.txt"
    )
    final_path = os.path.join(
        MEDIA_TMP_DIR, f"ad_final_{job_id}.mp4"
    )

    with open(list_file_path, "w") as f:
        for clip_path in clip_paths:
            f.write(
                f"file '{os.path.abspath(clip_path)}'\n"
            )

    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        final_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr_bytes = await process.communicate()

    if process.returncode != 0 or not os.path.exists(final_path):

        # Zaxira urinish: qayta kodlash bilan
        process2 = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            final_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr_bytes2 = await process2.communicate()

        if process2.returncode != 0 or not os.path.exists(final_path):
            error_text = stderr_bytes2.decode(
                "utf-8", errors="ignore"
            )[-800:]
            raise RuntimeError(
                f"ffmpeg birlashtirish (concat) xatosi: {error_text}"
            )

    try:
        os.remove(list_file_path)
    except Exception:
        pass

    asyncio.create_task(
        _delete_media_file_later(
            final_path,
            MEDIA_CLEANUP_DELAY_SECONDS,
        )
    )

    return final_path


async def run_ai_studio_job(
    job_id: str,
    chat_id: int,
    lang: str,
    brief: str,
    product_photo_bytes: bytes | None,
    voice_gender: str,
):
    """
    AI Studio'ning to'liq jarayoni: reja tuzish → har bir
    sahnani video+ovoz sifatida yaratish → barchasini
    birlashtirish. Har bosqichda video_jobs[job_id]["progress"]
    yangilanadi — frontend buni polling paytida ko'rsatadi.
    """

    video_jobs[job_id]["progress"] = t(
        lang, "ai_studio_planning"
    )

    try:

        scenes = await plan_ad_scenes(
            brief,
            lang,
            product_photo_bytes is not None,
        )

    except Exception:

        logger.exception(
            "AI Studio reja tuzish xatosi:"
        )

        await notify_admin_error_miniapp(
            "AI Studio — reja tuzish"
        )

        video_jobs[job_id] = {
            "status": "error",
            "detail": t(lang, "ai_studio_error"),
        }

        return

    scene_clip_paths: list[str] = []

    try:

        for idx, scene in enumerate(scenes):

            video_jobs[job_id]["progress"] = t(
                lang,
                "ai_studio_scene_progress",
                current=idx + 1,
                total=len(scenes),
            )

            visual_prompt = (
                scene.get("visual_prompt") or ""
            ).strip()
            voice_text = (
                scene.get("voice_text") or ""
            ).strip()

            if not visual_prompt:
                continue

            # Faqat BIRINCHI sahnada mahsulot rasmi bor bo'lsa,
            # uni boshlang'ich kadr sifatida ishlatamiz.
            scene_image_bytes = (
                product_photo_bytes
                if (idx == 0 and product_photo_bytes)
                else None
            )

            scene_video_url = await generate_fal_video(
                visual_prompt,
                "kling",
                aspect_ratio="9:16",
                duration="5",
                image_bytes=scene_image_bytes,
            )

            if not scene_video_url:
                continue

            if voice_text:

                try:

                    merged_path = await build_video_with_voiceover(
                        scene_video_url,
                        voice_text,
                        lang,
                        voice_gender,
                        f"{job_id}_scene{idx}",
                    )

                    scene_clip_paths.append(merged_path)

                    continue

                except Exception:

                    logger.exception(
                        f"AI Studio sahna {idx} ovoz xatosi "
                        "(ovozsiz davom etiladi):"
                    )

            # Ovoz bo'lmasa (yoki ovoz xato bersa), sahna videosini
            # baribir LOKAL faylga yuklab olamiz — concat faqat
            # lokal fayllar bilan ishlaydi.
            raw_scene_path = os.path.join(
                MEDIA_TMP_DIR,
                f"scene_{job_id}_{idx}.mp4",
            )

            os.makedirs(MEDIA_TMP_DIR, exist_ok=True)

            async with httpx.AsyncClient(timeout=120) as client:

                scene_resp = await client.get(scene_video_url)
                scene_resp.raise_for_status()

                with open(raw_scene_path, "wb") as f:
                    f.write(scene_resp.content)

            scene_clip_paths.append(raw_scene_path)

        if not scene_clip_paths:
            raise RuntimeError(
                "Hech qanday sahna muvaffaqiyatli "
                "yaratilmadi"
            )

        video_jobs[job_id]["progress"] = t(
            lang, "ai_studio_merging"
        )

        final_path = await concat_video_clips(
            scene_clip_paths,
            job_id,
        )

    except Exception:

        logger.exception(
            "AI Studio generatsiya xatosi:"
        )

        await notify_admin_error_miniapp(
            "AI Studio — generatsiya"
        )

        video_jobs[job_id] = {
            "status": "error",
            "detail": t(lang, "ai_studio_error"),
        }

        return

    finally:

        for p in scene_clip_paths:
            try:
                os.remove(p)
            except Exception:
                pass

    new_balance = change_balance(
        chat_id,
        -COIN_COST_AI_STUDIO,
    )

    video_jobs[job_id] = {
        "status": "done",
        "video_url": f"/api/media/{os.path.basename(final_path)}",
        "balance": new_balance,
        "cost": COIN_COST_AI_STUDIO,
    }


@api.post("/api/generate-ad-video")
async def api_generate_ad_video(
    init_data: str = Form(...),
    brief: str = Form(...),
    voice_gender: str = Form("female"),
    product_photo: UploadFile = None,
):
    """
    AI Studio kirish nuqtasi. Darhol job_id qaytaradi (huddi
    /api/generate-video kabi) — haqiqiy jarayon run_ai_studio_job
    orqali orqa fonda davom etadi. Frontend /api/video-status
    (bir xil endpoint!) orqali polling qiladi.
    """

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    lang = get_lang(chat_id)

    if get_balance(chat_id) < COIN_COST_AI_STUDIO:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_AI_STUDIO,
                balance=get_balance(chat_id),
            ),
        )

    product_photo_bytes = None

    if product_photo is not None:
        product_photo_bytes = await product_photo.read()

    job_id = uuid.uuid4().hex

    video_jobs[job_id] = {
        "status": "pending",
        "chat_id": chat_id,
        "progress": t(lang, "ai_studio_planning"),
    }

    asyncio.create_task(
        run_ai_studio_job(
            job_id,
            chat_id,
            lang,
            brief,
            product_photo_bytes,
            voice_gender,
        )
    )

    return {
        "job_id": job_id,
        "cost": COIN_COST_AI_STUDIO,
    }


@api.get("/api/media/{filename}")
async def api_get_media(filename: str):
    """
    Birlashtirilgan (video+ovoz) fayllarni xizmat qiladi.
    MUHIM: filename faqat MEDIA_TMP_DIR ichidan olinadi va
    "/" yoki ".." kabi belgilar bo'lsa rad etiladi — aks holda
    server diskidagi istalgan faylni o'qish mumkin bo'lib
    qolardi (path traversal zaifligi).
    """

    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="noto'g'ri fayl nomi")

    path = os.path.join(MEDIA_TMP_DIR, filename)

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="fayl topilmadi")

    return FileResponse(path, media_type="video/mp4")


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
    voice_text: str | None = None,
    voice_gender: str = "female",
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

    final_video_url = video_url
    has_voiceover = False

    # MUHIM (YANGI): agar foydalanuvchi "Video nima desin?"
    # matnini kiritgan bo'lsa VA model shuni qo'llab-quvvatlasa,
    # ovozni qo'shishga harakat qilamiz. Bu qadam xato bersa
    # (masalan ffmpeg hali sozlanmagan bo'lsa), BUTUN job
    # muvaffaqiyatsiz bo'lib qolmaydi — foydalanuvchiga baribir
    # ovozsiz video yetkaziladi, faqat admin'ga xabar boradi.
    if voice_text and model_key in VOICEOVER_ALLOWED_MODELS:

        try:

            merged_path = await build_video_with_voiceover(
                video_url,
                voice_text,
                lang,
                voice_gender,
                job_id,
            )

            final_video_url = (
                f"/api/media/{os.path.basename(merged_path)}"
            )

            has_voiceover = True

        except Exception:

            logger.exception(
                "Video+ovoz birlashtirish xatosi (ovozsiz "
                "video bilan davom etiladi):"
            )

            await notify_admin_error_miniapp(
                "Video+ovoz birlashtirish"
            )

    new_balance = change_balance(
        chat_id,
        -total_cost,
    )

    video_jobs[job_id] = {
        "status": "done",
        "video_url": final_video_url,
        "balance": new_balance,
        "cost": total_cost,
        "has_voiceover": has_voiceover,
    }


@api.post("/api/generate-video")
async def api_generate_video(
    init_data: str = Form(...),
    prompt: str = Form(...),
    model_key: str = Form("wan"),
    aspect_ratio: str = Form(None),
    duration: str = Form(None),
    frame: UploadFile = None,
    voice_text: str = Form(None),
    voice_gender: str = Form("female"),
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
        - voice_text — "video nima desin" (ixtiyoriy, faqat
          Kling/Kling Pro'da ishlaydi — VOICEOVER_ALLOWED_MODELS)
        - voice_gender — "female" / "male"

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
            voice_text,
            voice_gender,
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


@api.post("/api/analyze-video")
async def api_analyze_video(
    init_data: str = Form(...),
    video: UploadFile = None,
):
    """
    MUHIM (YANGI): Video Analyzer. Yuklangan videodan ffmpeg
    orqali bir necha kadr ajratiladi, so'ng Claude'ning ko'rish
    (vision) qobiliyati orqali tahlil qilinib, video-generatsiya
    modellari (Kling/Wan) uchun professional ingliz tilidagi
    prompt yaratiladi. Bu sinxron (darhol javob qaytaradigan)
    endpoint — chunki kadr ajratish + Claude tahlili odatda video
    generatsiyasidan ANCHA tezroq (bir necha o'n soniya), shuning
    uchun job/polling patterni shart emas.
    """

    user = verify_telegram_init_data(
        init_data
    )

    chat_id = user["id"]

    lang = get_lang(chat_id)

    if video is None:
        raise HTTPException(
            status_code=400,
            detail=t(lang, "video_missing"),
        )

    if get_balance(chat_id) < COIN_COST_VIDEO_ANALYZE:
        raise HTTPException(
            status_code=402,
            detail=t(
                lang,
                "insufficient_coins",
                cost=COIN_COST_VIDEO_ANALYZE,
                balance=get_balance(chat_id),
            ),
        )

    video_bytes = await video.read()

    job_id = uuid.uuid4().hex

    try:

        frame_paths = await extract_video_frames(
            video_bytes,
            job_id,
        )

        if not frame_paths:
            raise RuntimeError(
                "ffmpeg kadr ajrata olmadi "
                "(frame_paths bo'sh)"
            )

        analysis, generated_prompt = await analyze_video_with_claude(
            frame_paths
        )

    except Exception:

        logger.exception(
            "Mini App video tahlil xatosi:"
        )

        await notify_admin_error_miniapp(
            "Mini App video tahlil qilish"
        )

        raise HTTPException(
            status_code=500,
            detail=t(lang, "video_analyze_error"),
        )

    new_balance = change_balance(
        chat_id,
        -COIN_COST_VIDEO_ANALYZE,
    )

    return {
        "analysis": analysis,
        "generated_prompt": generated_prompt,
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
    voice_gender: str = Form("female"),
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

    # MUHIM (YANGI): endi ayol/erkak tanlovi qabul qilinadi.
    # Noma'lum qiymat kelsa (yoki umuman kelmasa) "female"ga
    # tushib qoladi — hech qachon xato bermaydi.
    selected_voice = get_tts_voice(
        lang,
        voice_gender,
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
