# ============================================================
#  patch_frontend.py
#  Portfolio HTML faylidagi "Aloqa" formasini backendga ulaydi:
#    eski:  window.location.href = 'mailto:...'   (email ilovasini ochadi)
#    yangi: fetch(BACKEND_URL + '/api/contact', {POST})  (serverga yuboradi)
#
#  Ishlatish:
#     python patch_frontend.py https://backend-manzilingiz.onrender.com
#     python patch_frontend.py            # default: http://127.0.0.1:8000
# ============================================================
import re
import os
import sys
import json
import shutil

HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Madaminjon Portfolio.html")
BACKUP_PATH = os.path.join(os.path.dirname(HTML_PATH), "Madaminjon Portfolio.backup.html")


def encode_template(t: str) -> str:
    """Template matnini JSON ga o'giradi va '</' ni '<\\/' qilib himoyalaydi.
    Aks holda matn ichidagi </script> HTML script-tegini erta yopib qo'yadi
    (original bundle ham aynan shunday qiladi)."""
    return json.dumps(t).replace("</", "<\\/")


def main() -> int:
    backend_url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

    if not os.path.exists(HTML_PATH):
        print(f"XATO: fayl topilmadi: {HTML_PATH}")
        return 1

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # --- template (JSON string) ni ajratib olamiz ---
    m = re.search(r'(<script type="__bundler/template">)(.*?)(</script>)', html, re.S)
    if not m:
        print("XATO: __bundler/template bloki topilmadi.")
        return 1

    template = json.loads(m.group(2))   # haqiqiy HTML/JS matni

    # --- 1) Forma submit-handler ni almashtiramiz ---
    new_handler = (
        "const form = document.getElementById('contact-form');\n"
        "    if (form) {\n"
        "      var BACKEND_URL = " + json.dumps(backend_url) + ";\n"
        "      form.addEventListener('submit', async function(e) {\n"
        "        e.preventDefault();\n"
        "        var fd = new FormData(form);\n"
        "        var status = document.getElementById('form-status');\n"
        "        var btn = form.querySelector('button[type=\"submit\"]') || form.querySelector('button');\n"
        "        var payload = {\n"
        "          name: (fd.get('name') || '').toString().trim(),\n"
        "          email: (fd.get('email') || '').toString().trim(),\n"
        "          message: (fd.get('message') || '').toString().trim(),\n"
        "          website: (fd.get('website') || '').toString()\n"
        "        };\n"
        "        if (status) { status.style.display = 'block'; status.textContent = 'Yuborilmoqda...'; }\n"
        "        if (btn) btn.disabled = true;\n"
        "        try {\n"
        "          var res = await fetch(BACKEND_URL + '/api/contact', {\n"
        "            method: 'POST',\n"
        "            headers: { 'Content-Type': 'application/json' },\n"
        "            body: JSON.stringify(payload)\n"
        "          });\n"
        "          if (!res.ok) throw new Error('HTTP ' + res.status);\n"
        "          if (status) status.textContent = 'Rahmat, ' + payload.name + '! Xabaringiz yuborildi.';\n"
        "          form.reset();\n"
        "        } catch (err) {\n"
        "          if (status) status.textContent = \"Xatolik yuz berdi. Keyinroq urinib ko'ring yoki yozing: atmadaminjon@gmail.com\";\n"
        "        } finally {\n"
        "          if (btn) btn.disabled = false;\n"
        "        }\n"
        "      });\n"
        "    }"
    )

    handler_re = re.compile(
        r"const form = document\.getElementById\('contact-form'\);.*?"
        r"setTimeout\(\(\) => \{ form\.reset\(\); \}, 400\);\s*\}\);\s*\}",
        re.S,
    )
    template, n1 = handler_re.subn(new_handler, template)

    # --- Agar sayt allaqachon ulangan bo'lsa: faqat BACKEND_URL ni yangilaymiz ---
    if n1 == 0 and "var BACKEND_URL =" in template:
        template, nu = re.subn(
            r"var BACKEND_URL = .*?;",
            "var BACKEND_URL = " + json.dumps(backend_url) + ";",
            template,
            count=1,
        )
        if nu:
            new_html = html[:m.start(2)] + encode_template(template) + html[m.end(2):]
            with open(HTML_PATH, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"Sayt allaqachon ulangan edi — backend manzili yangilandi: {backend_url}")
            return 0

    # --- 2) Spam himoyasi uchun yashirin "honeypot" maydon qo'shamiz ---
    honeypot = ('<input type="text" name="website" tabindex="-1" autocomplete="off" '
                'aria-hidden="true" style="position:absolute;left:-9999px;width:1px;'
                'height:1px;opacity:0;">')
    template, n2 = re.subn(
        r'(<form id="contact-form"[^>]*>)',
        lambda mm: mm.group(1) + honeypot,
        template,
        count=1,
    )

    # --- Natijani tekshiramiz ---
    if n1 == 0:
        print("DIQQAT: forma submit-handler topilmadi. "
              "Ehtimol sayt allaqachon ulangan yoki o'zgargan. Hech narsa yozilmadi.")
        return 1
    # Faqat FORMA-dagi mailto-redirect yo'qolganini tekshiramiz.
    # Aloqa bo'limidagi to'g'ridan-to'g'ri <a href="mailto:..."> havolasi qoladi.
    if "window.location.href = 'mailto:" in template:
        print("DIQQAT: formaning mailto bloki hali ham qoldi — to'xtatildi.")
        return 1

    print(f"  - submit-handler almashtirildi: {n1} ta")
    print(f"  - honeypot maydon qo'shildi:     {n2} ta")

    # --- Zaxira nusxa va yozish ---
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(HTML_PATH, BACKUP_PATH)
        print(f"  - zaxira saqlandi: {os.path.basename(BACKUP_PATH)}")

    new_html = html[:m.start(2)] + encode_template(template) + html[m.end(2):]
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"\nTAYYOR. Forma endi shu manzilga yuboradi: {backend_url}/api/contact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
