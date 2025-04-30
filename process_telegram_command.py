from datetime import datetime
from zoneinfo import ZoneInfo
from attendance_state import attendance_state
from send_telegram_alert import send_telegram_alert

async def process_telegram_command(message: str):
    if not message.startswith('/'):
        return  # Ignore non-command messages

    parts = message.split()
    command = parts[0].lower()

    try:
        if command == '/help':
            await send_telegram_alert("📋 *Commands:*\n/status - Bot status\n/holidays - List holidays\n/addleave YYYY-MM-DD - Add leave\n/removeleave YYYY-MM-DD - Remove leave\n/leavedays - List leaves", True)

        elif command == '/status':
            status = [
                f"🔹 Last success: {attendance_state.last_success_date or 'Never'}",
                f"🔹 Holidays: {len(attendance_state.holidays)}",
                f"🔹 Leave days: {len(attendance_state.leave_days)}"
            ]
            await send_telegram_alert("\n".join(status), True)

        elif command in ('/holidays', '/leavedays'):
            days = sorted(attendance_state.holidays if command == '/holidays' else attendance_state.leave_days)
            formatted_days = [datetime.strptime(date_str, '%Y-%m-%d').strftime('%b %-d, %Y') for date_str in days]
            message = f"🗓 {'Holidays' if command == '/holidays' else 'Leave Days'}:\n"
            message += "\n".join(formatted_days) if formatted_days else "None scheduled"
            await send_telegram_alert(message, True)

        elif command.startswith(('/addleave', '/removeleave')) and len(parts) > 2:
            month_str = parts[1]   # Extract month as string (e.g., 'May')
            day_str = parts[2]     # Extract day as string (e.g., '5')

            try:
                # Convert month name to number (e.g., 'May' -> 5)
                month = datetime.strptime(month_str, '%b').month
                day = int(day_str)

                today = datetime.now(ZoneInfo("Asia/Kathmandu"))
                current_year = today.year

                # Construct the date from the current year (e.g., 'May 5, 2025')
                target_date = datetime(current_year, month, day)

                # Compare if the target date is in the future or past within the same year
                if target_date < today:
                    await send_telegram_alert(f"❌ Cannot add leave for {month_str} {day}. The date is in the past.", False)
                    return

                # Add to leave days if it's a valid future date
                leave_date_str = target_date.strftime('%Y-%m-%d')
                attendance_state.leave_days.add(leave_date_str)
                attendance_state.save_state()

                if command.startswith('/addleave'):
                    msg = f"➕ Added leave: {month_str} {day}"
                else:
                    attendance_state.leave_days.discard(leave_date_str)
                    msg = f"➖ Removed leave: {month_str} {day}"

                await send_telegram_alert(msg, True)

            except ValueError:
                await send_telegram_alert("❌ Invalid date format. Please use 'Month Day' format (e.g., 'May 5').", False)

    except ValueError:
        await send_telegram_alert("❌ Invalid date format. Use YYYY-MM-DD", False)
    except Exception as e:
        await send_telegram_alert(f"⚠️ Error: {str(e)}", False)
