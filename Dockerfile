# MUHIM: bu fayl repo'ning ASOSIY (root) papkasida turishi kerak —
# bot.py, server.py bilan bir qatorda, webapp/ ichida EMAS.
#
# Bu fayl bo'lsa, Railway (va aksariyat boshqa platformalar) uni
# Nixpacks/Railpack o'rniga AVTOMATIK ustun qo'yib ishlatadi — shu
# sababli qaysi "quruvchi" ishlatilishidan qat'iy nazar, ffmpeg
# har doim o'rnatiladi.
#
# CACHE_BUST: 2026-09-26-v2 — bu qatorni har safar "bot.py topilmadi"
# kabi eskirgan (keshlangan) build muammosi bo'lsa, qiymatini
# o'zgartiring (masalan v3, v4...) — bu Railway/Docker'ni COPY
# qatlamini QAYTADAN, noldan bajarishga majburlaydi.

FROM python:3.11-slim

# ffmpeg — video+ovoz birlashtirish (build_video_with_voiceover),
# Video Analyzer (kadr ajratish) va AI Studio (sahnalarni
# birlashtirish) uchun kerak.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# MUHIM: agar sizning requirements fayli boshqa nom bilan
# saqlangan bo'lsa (masalan requirements.txt o'rniga boshqa nom),
# quyidagi ikki qatordagi "requirements.txt"ni o'sha nomga
# almashtiring.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CACHE_BUST shu yerda ham ishlatiladi — COPY buyrug'idan oldin
# qo'yilgan har qanday o'zgargan qator undan keyingi barcha
# qatlamlarni (jumladan COPY . .) keshdan chiqarib, qaytadan
# bajarishga majburlaydi.
ARG CACHE_BUST=2026-09-26-v2
COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
