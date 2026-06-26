# ============================================================
#  Madaminjon Portfolio — Backend (FastAPI)
# ------------------------------------------------------------
#  Vazifasi:
#    1) Saytdagi "Aloqa" formasidan kelgan xabarlarni qabul qilish
#    2) Xabarni SQLite bazaga saqlash
#    3) Telegram botga yuborish (darhol xabar olasiz)
#    4) Email (Gmail) ga yuborish
#    5) Parol bilan himoyalangan /admin panelda xabarlarni ko'rish
#
#  Ishga tushirish:   uvicorn app:app --reload
#  Hujjat:            README.md ga qarang
# ============================================================

import os
import html
import sqlite3
import secrets
from datetime import datetime, timezone
from contextlib import closing

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, field_validator

# --- .env faylidan sozlamalarni o'qish ---
load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages.db")


# ------------------------------------------------------------
#  Ma'lumotlar bazasi (SQLite)
# ------------------------------------------------------------
def init_db() -> None:
    """Baza va 'messages' jadvalini (agar mavjud bo'lmasa) yaratadi."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL,
                message    TEXT NOT NULL,
                ip         TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_message(name: str, email: str, message: str, ip: str) -> int:
    """Xabarni bazaga yozadi va yangi qatorning id sini qaytaradi."""
    created = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "INSERT INTO messages (name, email, message, ip, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, message, ip, created),
        )
        conn.commit()
        return cur.lastrowid


def list_messages() -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def delete_message(msg_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        conn.commit()


# ------------------------------------------------------------
#  Bildirishnoma: Telegram
#  ("best-effort" — xato bo'lsa ham forma ishlayveradi)
# ------------------------------------------------------------
async def send_telegram(name: str, email: str, message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # sozlanmagan — o'tkazib yuboramiz
    # HTML parse_mode + escape: foydalanuvchi matnidagi maxsus belgilar
    # (_, *, [, <, > va h.k.) xabarni buzmaydi.
    text = (
        "📩 <b>Portfolio orqali yangi xabar</b>\n\n"
        f"👤 <b>Ism:</b> {html.escape(name)}\n"
        f"✉️ <b>Email:</b> {html.escape(email)}\n\n"
        f"💬 {html.escape(message)}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
    except Exception as e:
        print(f"[telegram] yuborilmadi: {e}")


# ------------------------------------------------------------
#  FastAPI ilovasi
# ------------------------------------------------------------
app = FastAPI(title="Madaminjon Portfolio API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# --- Forma ma'lumotlari uchun model (validatsiya) ---
class ContactIn(BaseModel):
    name: str
    email: EmailStr
    message: str
    # Honeypot (spam-bot tutqichi): odam bu maydonni ko'rmaydi/to'ldirmaydi.
    website: str | None = None

    @field_validator("name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Maydon bo'sh bo'lmasligi kerak")
        if len(v) > 5000:
            raise ValueError("Juda uzun")
        return v


def client_ip(request: Request) -> str:
    # Reverse-proxy (Render/Railway) orqasida bo'lsa haqiqiy IP shu yerda bo'ladi
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


@app.get("/")
def health():
    return {"ok": True, "service": "Madaminjon Portfolio API"}


@app.post("/api/contact")
async def contact(data: ContactIn, request: Request):
    # Spam-bot honeypot maydonni to'ldiradi — jimgina "muvaffaqiyat" qaytaramiz
    if data.website:
        return JSONResponse({"ok": True})

    ip = client_ip(request)
    save_message(data.name, str(data.email), data.message, ip)

    # Telegramga yuboramiz (xato bo'lsa ham forma ishlayveradi)
    await send_telegram(data.name, str(data.email), data.message)
    return {"ok": True, "message": "Xabaringiz qabul qilindi. Rahmat!"}


# ------------------------------------------------------------
#  Admin panel (HTTP Basic auth bilan himoyalangan)
# ------------------------------------------------------------
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    ok_user = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    ok_pass = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def render_admin(messages: list[dict]) -> str:
    rows = []
    for m in messages:
        # html.escape — XSS himoyasi (foydalanuvchi yuborgan matnni xavfsiz chiqaramiz)
        name = html.escape(m["name"])
        email = html.escape(m["email"])
        msg = html.escape(m["message"]).replace("\n", "<br>")
        created = html.escape(m["created_at"])[:19].replace("T", " ")
        ip = html.escape(m.get("ip") or "")
        rows.append(f"""
        <div class="card">
          <div class="head">
            <div>
              <strong>{name}</strong>
              <a href="mailto:{email}">{email}</a>
            </div>
            <form method="post" action="/admin/delete/{m['id']}"
                  onsubmit="return confirm('Ushbu xabar o\\'chirilsinmi?')">
              <button class="del">O'chirish</button>
            </form>
          </div>
          <p class="body">{msg}</p>
          <div class="meta">{created} UTC · IP: {ip} · #{m['id']}</div>
        </div>""")

    body = "".join(rows) if rows else "<p class='empty'>Hozircha xabarlar yo'q.</p>"
    return f"""<!doctype html>
<html lang="uz"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin — Xabarlar</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#0c0c12; color:#e8e8ef;
         font-family:-apple-system,Segoe UI,Roboto,sans-serif; padding:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:#8a8a98; font-size:14px; margin-bottom:24px; }}
  .card {{ background:#15151f; border:1px solid #25252f; border-radius:14px;
          padding:16px 18px; margin-bottom:14px; max-width:760px; }}
  .head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; }}
  .head a {{ color:#5b9dff; text-decoration:none; margin-left:10px; font-size:14px; }}
  .body {{ margin:12px 0 8px; line-height:1.6; white-space:pre-wrap; }}
  .meta {{ color:#62626f; font-size:12px; }}
  .del {{ background:#2a1215; color:#ff8a80; border:1px solid #5c2b2e;
          border-radius:8px; padding:6px 12px; cursor:pointer; font-size:13px; }}
  .del:hover {{ background:#3a181c; }}
  .empty {{ color:#8a8a98; }}
</style></head>
<body>
  <h1>📬 Kelgan xabarlar</h1>
  <div class="sub">Jami: {len(messages)} ta</div>
  {body}
</body></html>"""


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(_: str = Depends(require_admin)):
    return render_admin(list_messages())


@app.post("/admin/delete/{msg_id}")
def admin_delete(msg_id: int, _: str = Depends(require_admin)):
    delete_message(msg_id)
    return RedirectResponse(url="/admin", status_code=303)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
