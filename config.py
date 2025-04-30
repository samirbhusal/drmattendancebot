import os
from dotenv import load_dotenv

load_dotenv()

# Store your configuration settings here
LOGIN_URL = os.getenv('LOGIN_URL')
ATTENDANCE_URL = os.getenv('PUNCH_IN_URL')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
USER_IP = os.getenv('USER_IP')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
