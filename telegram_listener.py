import aiohttp
import asyncio
from config import TELEGRAM_BOT_TOKEN
from process_telegram_command import process_telegram_command
from datetime import datetime
from zoneinfo import ZoneInfo  # Import ZoneInfo for time zone handling

async def telegram_listener():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    offset = None

    # Set Kathmandu timezone
    kathmandu_tz = ZoneInfo("Asia/Kathmandu")

    while True:
        now = datetime.now(tz=kathmandu_tz)  # Get current time in Kathmandu time zone

        # Only run the bot between 9 AM and 10 PM Kathmandu time
        if now.hour < 8 or now.hour >= 22:
            print(f"Outside working hours ({now.strftime('%I:%M %p')}), bot is idle.")
            await asyncio.sleep(60)  # Sleep for 1 minute before checking again
            continue

        try:
            async with aiohttp.ClientSession() as session:
                params = {'timeout': 30}  # Polling every 30 seconds
                if offset is not None:
                    params['offset'] = offset
                async with session.get(url, params=params) as res:
                    updates = await res.json()

                    if 'result' in updates:
                        for update in updates['result']:
                            offset = update['update_id'] + 1
                            if msg := update.get('message', {}).get('text'):
                                await process_telegram_command(msg)
                    else:
                        print(f"No new updates, waiting... {now.strftime('%I:%M %p')}")

            await asyncio.sleep(10)  # Sleep for 10 seconds before checking again

        except Exception as e:
            print(f"Listener error: {e}")
            await asyncio.sleep(5)