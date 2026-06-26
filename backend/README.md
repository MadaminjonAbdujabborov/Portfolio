# Madaminjon Portfolio — Backend

Portfolio saytining "Aloqa" formasi uchun kichik backend.
Forma to'ldirilganda xabar:

1. **SQLite bazaga** saqlanadi,
2. **Telegram botingizga** yuboriladi,
3. **/admin** panelда (parol bilan) ko'rinadi.

Texnologiya: **Python + FastAPI**.

---

## 1. Lokal (kompyuterda) ishga tushirish

```powershell
cd "f:\Saytg ama'lumotlar\backend"

# 1) Virtual muhit yaratish (bir marta)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3) Sozlamalar faylini yaratish
copy .env.example .env
#  -> .env faylini ochib qiymatlarni to'ldiring (pastga qarang)

# 4) Serverni ishga tushirish
uvicorn app:app --reload
```

So'ng brauzerда:
- API: <http://127.0.0.1:8000/>
- Admin panel: <http://127.0.0.1:8000/admin>

---

## 2. `.env` ni to'ldirish

### 🔐 Admin panel
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=kuchli_parol_yozing
```

### 📲 Telegram bot
1. Telegramda **@BotFather** ga yozing → `/newbot` → bot nomini kiriting → **token** olasiz.
   `TELEGRAM_BOT_TOKEN` ga shu tokenni qo'ying.
2. Yangi botingizga Telegramда **`/start`** deb yozing (bu muhim!).
3. **Chat ID** ni aniqlash:
   - Brauzerда oching:
     `https://api.telegram.org/bot<TOKEN>/getUpdates`
     (`<TOKEN>` o'rniga o'z tokeningizni qo'ying)
   - Javobда `"chat":{"id":123456789, ...}` ko'rinadi — shu raqam sizning `TELEGRAM_CHAT_ID`.
   - Eslatma: avval botga `/start` yozmasangiz `getUpdates` bo'sh chiqadi.

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

> Xabarlar faqat **Telegram**ga yuboriladi (email ishlatilmaydi).

---

## 3. Saytni backendga ulash

`Madaminjon Portfolio.html` formasi backendga `POST /api/contact` so'rovini
yuboradigan qilib o'zgartiriladi. Patch skripti tayyor:

```powershell
python patch_frontend.py https://SIZNING-BACKEND-MANZILINGIZ
```

(Lokal test uchun: `python patch_frontend.py http://127.0.0.1:8000`)

Bu skript HTML faylini avtomatik yangilaydi va eski nusxani
`Madaminjon Portfolio.backup.html` deb saqlaydi.

---

## 4. Bepul hostingга joylash (tavsiya)

### Backend → Render.com (bepul)
1. `backend/` papkasini GitHub repozitoriyasiga yuklang.
2. <https://render.com> → **New → Web Service** → repo'ni ulang.
3. Sozlamalar:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. **Environment** bo'limida `.env` dagi barcha o'zgaruvchilarni qo'shing
   (ADMIN_PASSWORD, TELEGRAM_*, SMTP_* va h.k.).
5. Deploy tugagach sizga manzil beriladi, masalan
   `https://madaminjon-portfolio.onrender.com`.
6. Shu manzilни `ALLOWED_ORIGINS` ga emas — saytingiz domeniни `ALLOWED_ORIGINS`
   ga yozing. Backend manzilini esa `patch_frontend.py` ga bering.

> Eslatma: Render bepul tarifда SQLite fayli qayta deploy'да o'chishi mumkin.
> Xabarlar Telegram/email orqali baribir keladi. Doimiy baza kerak bo'lsa,
> Render'ning bepul PostgreSQL'iga o'tkazamiz (so'rang).

### Sayt (statik HTML) → Netlify yoki Cloudflare Pages (bepul)
- `Madaminjon Portfolio.html` ni `index.html` deb nomlab,
  Netlify'ga "drag & drop" qiling — tamom.

---

## Fayllar
| Fayl | Vazifasi |
|------|----------|
| `app.py` | Asosiy backend (API + admin panel) |
| `requirements.txt` | Python kutubxonalari |
| `.env.example` | Sozlamalar namunasi |
| `patch_frontend.py` | Saytdagi formani backendga ulash skripti |
| `Procfile` | Hosting uchun ishga tushirish buyrug'i |
| `messages.db` | SQLite bazasi (avtomatik yaratiladi) |
