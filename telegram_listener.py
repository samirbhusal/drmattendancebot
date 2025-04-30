# telegram_listener.py

import aiohttp
import asyncio
from config import TELEGRAM_BOT_TOKEN
from process_telegram_command import process_telegram_command

async def telegram_listener():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    offset = None

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                params = {'timeout': 30}
                if offset is not None:
                    params['offset'] = offset
                async with session.get(url, params=params) as res:
                    updates = await res.json()
                    for update in updates.get('result', []):
                        offset = update['update_id'] + 1
                        if msg := update.get('message', {}).get('text'):
                            await process_telegram_command(msg)
        except Exception as e:
            print(f"Listener error: {e}")
            await asyncio.sleep(5)
