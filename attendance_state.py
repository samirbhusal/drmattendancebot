import json
from datetime import datetime
from token_store import TokenStore

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
