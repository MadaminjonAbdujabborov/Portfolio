# Chat ID ni .env ga yozadi va botga test xabar yuboradi
import os, sys, json, urllib.request, urllib.parse
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
chat_id = sys.argv[1] if len(sys.argv) > 1 else ""

# .env dagi TELEGRAM_CHAT_ID qatorini yangilaymiz (tokenга tegmaymiz)
with open(ENV_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()
found = False
for i, line in enumerate(lines):
    if line.strip().startswith("TELEGRAM_CHAT_ID="):
        lines[i] = f"TELEGRAM_CHAT_ID={chat_id}\n"
        found = True
        break
if not found:
    lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
with open(ENV_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)
print(f".env yangilandi: TELEGRAM_CHAT_ID={chat_id}")

# Test xabar yuboramiz
load_dotenv(ENV_PATH)
token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
text = ("✅ Test: backend Telegramga ulandi!\n\n"
        "Endi saytdagi 'Aloqa' formasidan kelgan har bir xabar shu yerga keladi.")
payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=15) as r:
        res = json.load(r)
    print("TEST XABAR:", "yuborildi ✅" if res.get("ok") else f"xato: {res}")
except Exception as e:
    print(f"XATO: {e}")
