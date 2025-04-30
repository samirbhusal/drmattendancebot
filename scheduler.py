import asyncio
import random
from run_attendance import is_working_day, run_attendance
from send_telegram_alert import send_telegram_alert
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from attendance_state import AttendanceState

attendance_state = AttendanceState()


async def scheduler():
    """
    Schedules the attendance logic to run at a specific time each day.
    """
    kathmandu_tz = ZoneInfo("Asia/Kathmandu")
    now = datetime.now(tz=kathmandu_tz)
    today_str = now.strftime("%Y-%m-%d")

    # If attendance is already marked today, just listen for commands
    if attendance_state.last_success_date == today_str:
        await send_telegram_alert(
            "Attendance already marked today. Listening for commands only.", True
        )
    else:
        start_time = now.replace(hour=8, minute=45, second=0, microsecond=0)
        end_time = now.replace(hour=9, minute=10, second=0, microsecond=0)

        if now > end_time:
            start_time += timedelta(days=1)
            end_time += timedelta(days=1)

        delay_seconds = random.randint(0, int((end_time - start_time).total_seconds()))
        target_time = start_time + timedelta(seconds=delay_seconds)

        # Skip to next working day if target_time falls on a holiday or leave
        while not await is_working_day(attendance_state, target_time.date()):
            target_time += timedelta(days=1)

        # Instead of resetting to static start_time, keep the random target_time
        wait_seconds = (target_time - now).total_seconds()

        await send_telegram_alert(
            f"Next Attendance will be marked on:  {target_time.strftime('%I:%M %p, %b %-d, %Y')} ",
            True,
        )
        await asyncio.sleep(wait_seconds)

        try:
            if await run_attendance():
                attendance_state.last_success_date = today_str
                attendance_state.save_state()
                await send_telegram_alert(
                    "✅ Attendance successful. Listening for commands only.", True
                )
        except Exception as e:
            await send_telegram_alert(f"❌ Attendance attempt failed: {str(e)}", False)

    while True:
        await asyncio.sleep(30)
