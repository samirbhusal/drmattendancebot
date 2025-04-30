import os
import aiohttp
from datetime import date, datetime
from send_telegram_alert import send_telegram_alert
from attendance_state import AttendanceState
from dotenv import load_dotenv
from config import LOGIN_URL,ATTENDANCE_URL,USER_IP

# Load environment variables from .env
load_dotenv()

attendance_state = AttendanceState()

async def login(session: aiohttp.ClientSession):
    
    # If a valid token is available, use it
    if attendance_state.token_store.is_valid():
        await send_telegram_alert("Using cached token", True)
        return attendance_state.token_store.token

    # If no valid token, request a new one from the login API
    try:
        async with session.post(
            LOGIN_URL,
            json={'email': os.getenv('USERNAME'), 'password': os.getenv('PASSWORD')},
            headers={'Content-Type': 'application/json'},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if 'access_token' not in data:
                raise ValueError("No token received in the response.")
            
            token = data['access_token']
            expires_in = data.get('expires_in', '2h')
            attendance_state.token_store.set_token(token, expires_in)
            await send_telegram_alert("Login successful", True)
            return token
    except Exception as e:
        await send_telegram_alert(f"⚠️ Login failed: {str(e)}", False)
        raise

async def mark_attendance(session: aiohttp.ClientSession, token: str):
    """
    Marks the attendance by sending a POST request to the attendance API.
    """
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
                await send_telegram_alert("✅ Attendance marked successfully.", True)
                return True
            elif data.get('message') == "Already punched in!":
                await send_telegram_alert("✅ Attendance already marked today.", True)
                return True
            else:
                await send_telegram_alert(f"❌ Error: {data.get('message', 'Unknown error')}", False)
                return False
    except Exception as e:
        await send_telegram_alert(f"❌ Error marking attendance: {str(e)}", False)
        raise

async def is_working_day(attendance_state, check_date: date = None):
    """
    Determines if the given date is a working day.
    If no date is provided, it checks for today.
    """
    if check_date is None:
        check_date = datetime.now().date()
        
    date_str = check_date.strftime('%Y-%m-%d')

    # Check if it's a weekend
    if check_date.weekday() >= 5:
        return False

    # Check if it's a holiday or leave day
    if date_str in attendance_state.holidays.union(attendance_state.leave_days):
        return False

    return True

async def run_attendance():
    """
    The function to mark attendance if today is a working day and conditions are met.
    It checks if today is a working day and then proceeds with attendance marking.
    """

    # Check if today is a working day
    if await is_working_day(attendance_state):
        async with aiohttp.ClientSession() as session:
            # Login to get the token
            token = await login(session)

            # Mark attendance using the token
            if await mark_attendance(session, token):
                attendance_state.last_success_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                attendance_state.save_state()
                await send_telegram_alert("✅ Attendance marked successfully.", True)
            else:
                await send_telegram_alert("❌ Failed to mark attendance.", False)
    else:
        await send_telegram_alert("❌ Today is not a working day or is a holiday.", False)
