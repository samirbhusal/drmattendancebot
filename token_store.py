from datetime import datetime, timedelta
import re

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
