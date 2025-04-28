import json
import asyncio
import aiohttp
import random
import os
import re
from datetime import date, datetime, timedelta
from tenacity import retry, wait_fixed, stop_after_attempt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LOGIN_URL = os.getenv('LOGIN_URL')
ATTENDANCE_URL = os.getenv('PUNCH_IN_URL')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
USER_IP = os.getenv('USER_IP')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

class TokenStore:
    def __init__(self):
        self.token = None
        self.expires_at = None

    def is_valid(self):
        return self.token and self.expires_at and datetime.now() < self.expires_at

    def set_token(self, token, expires_in="2h"):
        self.token = token
        seconds = self._parse_duration(expires_in)
        self.expires_at = datetime.now() + timedelta(seconds=seconds)

    def _parse_duration(self, duration_str):
        hours = minutes = 0
        if match := re.search(r'(\d+)h', duration_str or ""):
            hours = int(match.group(1))
        if match := re.search(r'(\d+)m', duration_str or ""):
            minutes = int(match.group(1))
        return hours * 3600 + minutes * 60

    def clear(self):
        self.token = None
        self.expires_at = None

class AttendanceState:
    def __init__(self):
        self.last_success_date = None
        self.holidays = set()
        self.leave_days = set()
        self.token_store = TokenStore()
        self.load_state()

        current_year = datetime.now().year
        self.holidays.add(f"{current_year}-01-01")  # New Year's Day
        self.holidays.add(f"{current_year}-12-25")  # Christmas Day
        self.holidays.add(f"{current_year}-05-01")  # Labor Day (May 1)

    def save_state(self):
        with open('attendance_state.json', 'w') as f:
            json.dump({
                'last_success_date': self.last_success_date,
                'holidays': list(self.holidays),
                'leave_days': list(self.leave_days),
                'token': self.token_store.token,
                'token_expiry': self.token_store.expires_at.isoformat() if self.token_store.expires_at else None
            }, f)

    def load_state(self):
        try:
            with open('attendance_state.json', 'r') as f:
                data = json.load(f)
                self.last_success_date = data.get('last_success_date')
                self.holidays = set(data.get('holidays', []))
                self.leave_days = set(data.get('leave_days', []))
                if token := data.get('token'):
                    expires_at = datetime.fromisoformat(data['token_expiry']) if data.get('token_expiry') else None
                    if expires_at and expires_at > datetime.now():
                        self.token_store.token = token
                        self.token_store.expires_at = expires_at
        except (FileNotFoundError, json.JSONDecodeError):
            pass

attendance_state = AttendanceState()

async def send_telegram_alert(message: str, is_success: bool):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing - skipping notification")
        return

    emoji = "✅" if is_success else "❌"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    timestamp = datetime.now().strftime('%B %d, %Y')

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
        print(f"Failed to send Telegram alert: {e}")

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
async def login(session):
    if attendance_state.token_store.is_valid():
        await send_telegram_alert("Using cached token", True)
        return attendance_state.token_store.token

    try:
        async with session.post(
            LOGIN_URL,
            json={'email': USERNAME, 'password': PASSWORD},
            headers={'Content-Type': 'application/json'},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if not (token := data.get('access_token')):
                raise ValueError("No token in response")
            attendance_state.token_store.set_token(token, data.get('expires_in', '2h'))
            await send_telegram_alert("Login successful", True)
            return token
    except aiohttp.ClientResponseError as e:
        if e.status == 401:
            attendance_state.token_store.clear()
            await send_telegram_alert("⚠️ Invalid credentials", False)
        raise

async def mark_attendance(session, token):
    try:
        async with session.post(
            ATTENDANCE_URL,
            json={'token': token, 'ip': USER_IP},
            headers={'Content-Type': 'application/json'},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if data.get('status') == 'success':
                return True
            else:
                raise Exception("Failed to mark attendance")
    except Exception as e:
        print(f"Error marking attendance: {e}")
        raise

async def process_telegram_command(message: str):
    if not message.startswith('/'):
        return

    parts = message.split()
    command = parts[0].lower()

    try:
        if command == '/help':
            await send_telegram_alert("\ud83d\udccb *Commands:*\n/status - Bot status\n/holidays - List holidays\n/addleave YYYY-MM-DD - Add leave\n/removeleave YYYY-MM-DD - Remove leave\n/leavedays - List leaves", True)

        elif command == '/status':
            status = [
                f"\ud83d\udd39 Last success: {attendance_state.last_success_date or 'Never'}",
                f"\ud83d\udd39 Holidays: {len(attendance_state.holidays)}",
                f"\ud83d\udd39 Leave days: {len(attendance_state.leave_days)}"
            ]
            await send_telegram_alert("\n".join(status), True)

        elif command in ('/holidays', '/leavedays'):
            # Determine which set to use based on the command
            days = sorted(attendance_state.holidays if command == '/holidays' else attendance_state.leave_days)

            # Format the days in 'May 1, 2025' style
            formatted_days = [datetime.strptime(date_str, '%Y-%m-%d').strftime('%b %-d, %Y') for date_str in days]

            # Build the message
            message = f"\ud83d\uddd3 {'Holidays' if command == '/holidays' else 'Leave Days'}:\n"
            message += "\n".join(formatted_days) if formatted_days else "None scheduled"
            await send_telegram_alert(f"\ud83d\uddd3 {'Holidays' if command == '/holidays' else 'Leave Days'}:\n" + ("\n".join(formatted_days) if formatted_days else "None scheduled"), True)

        elif command.startswith(('/addleave', '/removeleave')) and len(parts) > 1:
            date_str = parts[1]
            datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()

            # Check if the date is in the past
            if datetime.strptime(date_str, '%Y-%m-%d').date() < today:
                await send_telegram_alert("❌ Cannot add or remove past leave dates", False)
                return
        
            elif command.startswith('/addleave'):
                attendance_state.leave_days.add(date_str)
                msg = f"\u2795 Added leave: {date_str}"
            else:
                attendance_state.leave_days.discard(date_str)
                msg = f"\u2796 Removed leave: {date_str}"
            attendance_state.save_state()
            await send_telegram_alert(msg, True)

    except ValueError:
        await send_telegram_alert("\u274c Invalid date format. Use YYYY-MM-DD", False)
    except Exception as e:
        await send_telegram_alert(f"\u26a0\ufe0f Error: {str(e)}", False)

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

async def is_working_day():
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    if today.weekday() >= 5:
        return False
    if today_str in attendance_state.holidays.union(attendance_state.leave_days):
        return False
    return True

async def run_attendance():
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        return await mark_attendance(session, token)

async def scheduler():
    asyncio.create_task(telegram_listener())

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    if attendance_state.last_success_date == today_str:
        await send_telegram_alert("Attendance already marked today. Listening for commands only.", True)
    elif not await is_working_day():
        await send_telegram_alert("Today is not a working day. Listening for commands only.", True)
    else:
        # Set the time range between 8:45 AM and 9:10 AM
        start_time = now.replace(hour=8, minute=45, second=0, microsecond=0)
        end_time = now.replace(hour=9, minute=10, second=0, microsecond=0)
        
        if now > end_time:  # If current time is past the range, schedule for the next day
            start_time += timedelta(days=1)
            end_time += timedelta(days=1)

        # Calculate the random delay between start_time and end_time
        delay_seconds = random.randint(0, int((end_time - start_time).total_seconds()))
        target_time = start_time + timedelta(seconds=delay_seconds)

        wait_seconds = (target_time - now).total_seconds()
        await send_telegram_alert(f"Waiting until {target_time.strftime('%H:%M:%S')} to mark attendance.", True)
        await asyncio.sleep(wait_seconds)

        try:
            if await run_attendance():
                attendance_state.last_success_date = today_str
                attendance_state.save_state()
                await send_telegram_alert("✅ Attendance successful. Listening for commands only.", True)
        except Exception as e:
            await send_telegram_alert(f"❌ Attendance attempt failed: {str(e)}", False)

    while True:
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(scheduler())
    except (KeyboardInterrupt, Exception) as e:
        asyncio.run(send_telegram_alert(f"\ud83d\udea9 Bot stopped due to: {str(e)}", False))