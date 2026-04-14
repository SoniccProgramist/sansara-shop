import requests
from django.conf import settings

def send_telegram_message(text: str) -> tuple[bool, str]:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token:
        return False, "TELEGRAM_BOT_TOKEN is missing"
    if not chat_id:
        return False, "TELEGRAM_CHAT_ID is missing"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, data=data, timeout=10)
        return (r.status_code == 200), f"{r.status_code} {r.text}"
    except requests.RequestException as e:
        return False, f"RequestException: {e}"