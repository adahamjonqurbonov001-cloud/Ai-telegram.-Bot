"""
MUBORAKXON — Agent Router
Natural-language router for existing bot capabilities.

This module does NOT generate media itself. It only decides which
existing MUBORAKXON capability should handle the request.
"""

import json
import re
from typing import Any


AGENT_SYSTEM_PROMPT = """
Siz MUBORAKXON Telegram AI botining Agent routerisiz.
Foydalanuvchi tabiiy tilda nima xohlayotganini aniqlang va faqat
quyidagi JSON formatida javob bering:

{
  "action": "chat|image|video|voice|music|style|balance|bonus|help|new_chat",
  "prompt": "foydalanuvchining media uchun asosiy topshirig'i",
  "model": "wan|kling|null"
}

Qoidalar:
- Oddiy savol, maslahat, tarjima yoki suhbat -> chat
- Rasm yaratish -> image
- Video yaratish -> video
- Matnni ovozga aylantirish -> voice
- Qo'shiq/musiqa yaratish -> music
- Yuborilgan rasmga stil berish haqida gap ketsa -> style
- Balans/coin haqida -> balance
- Kunlik bonus haqida -> bonus
- Yordam/foydalanish haqida -> help
- Yangi suhbat/boshlash -> new_chat
- "rasm qil", "surat yarat", "picture" kabi ma'nolar image.
- "video qil", "animatsiya qil" kabi ma'nolar video.
- "ovozga aylantir", "o'qib ber" kabi ma'nolar voice.
- "qo'shiq yarat", "musiqa qil" kabi ma'nolar music.
- Video model aytilmagan bo'lsa model=null qiling. Dastur keyin arzon Wan modelini tanlaydi.
- prompt qisqa, aniq va foydalanuvchi aytgan mazmunga mos bo'lsin.
- JSONdan tashqari hech qanday matn yozmang.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()

    # Markdown code fence bo'lsa olib tashlaymiz.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass

    # Javob ichidan birinchi JSON objectni topish.
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        try:
            value = json.loads(match.group(0))
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    return {}


async def classify_agent_request(
    claude_client,
    user_text: str,
    lang: str = "uz",
) -> dict[str, str]:
    """Claude yordamida foydalanuvchi topshirig'ini route qiladi."""

    response = await __import__("asyncio").to_thread(
        lambda: claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=AGENT_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Interfeys tili: {lang}\n"
                        f"Foydalanuvchi topshirig'i:\n{user_text}"
                    ),
                }
            ],
        )
    )

    raw = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", "") == "text"
    )

    data = _extract_json(raw)

    allowed = {
        "chat", "image", "video", "voice", "music",
        "style", "balance", "bonus", "help", "new_chat",
    }

    action = str(data.get("action", "chat")).lower().strip()
    if action not in allowed:
        action = "chat"

    prompt = str(data.get("prompt", "")).strip()
    model = str(data.get("model", "")).lower().strip()

    if model not in {"wan", "kling"}:
        model = ""

    return {
        "action": action,
        "prompt": prompt,
        "model": model,
    }
