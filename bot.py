from scheduler import scheduler
import asyncio

from send_telegram_alert import send_telegram_alert

if __name__ == "__main__":
    try:
        # Run the scheduler to start the bot
        asyncio.run(scheduler())
    except (KeyboardInterrupt, Exception) as e:
        asyncio.run(send_telegram_alert(f"Bot stopped due to: {str(e)}", False))