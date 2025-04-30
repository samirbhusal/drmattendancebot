# telegram_alerts.py

import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def send_telegram_alert(message: str, is_success: bool):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing - skipping notification")
        return

    emoji = "✅" if is_success else "❌"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    timestamp = datetime.now(ZoneInfo("Asia/Kathmandu")).strftime('%b %-d, %Y')

    payload = {
        'chat_id': str(TELEGRAM_CHAT_ID),
        'text': f"{emoji} Attendance Bot - {timestamp}\n{message}",
        'parse_mode': 'Markdown'
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error = await response.text()
                    print(f"Telegram API error: {error}")
    except Exception as e:
        send_telegram_alert(f"Failed to send Telegram alert: {e}")