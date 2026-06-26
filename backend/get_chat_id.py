# .env dagi token orqali Telegram chat ID ni topadi (tokenni ekranga chiqarmaydi)
import os, json, urllib.request
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()

if not token or ":" not in token:
    print("XATO: .env dagi TELEGRAM_BOT_TOKEN bo'sh yoki noto'g'ri. Tokenni tekshiring.")
    raise SystemExit(1)

# Botning o'zi to'g'ri ekanini tekshiramiz
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=15) as r:
        me = json.load(r)
    if not me.get("ok"):
        print("XATO: token noto'g'ri (getMe ishlamadi).")
        raise SystemExit(1)
    print(f"Bot topildi: @{me['result'].get('username')}  ({me['result'].get('first_name')})")
except Exception as e:
    print(f"XATO: Telegramга ulanib bo'lmadi: {e}")
    raise SystemExit(1)

# Yangilanishlardan chat ID larni yig'amiz
with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15) as r:
    data = json.load(r)

chats = {}
for upd in data.get("result", []):
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat = msg.get("chat")
    if chat:
        chats[chat["id"]] = chat.get("first_name") or chat.get("title") or chat.get("username") or "?"

if not chats:
    print("\nHech qanday suhbat topilmadi.")
    print("=> Telegramда botingizga kirib '/start' yoki biror xabar yozing, keyin qayta ishga tushiring.")
    raise SystemExit(2)

print("\nTopilgan chat(lar):")
for cid, name in chats.items():
    print(f"   chat_id = {cid}   ({name})")

# Faylga yozish uchun birinchisini chiqaramiz
first = list(chats.keys())[0]
print(f"\nCHAT_ID={first}")
