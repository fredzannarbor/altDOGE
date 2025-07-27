from src.database import Database
from typing import Optional
import hashlib

class AuthManager:
    def __init__(self, db: Database):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[int]:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE username = ? AND password_hash = ?"
        result = self.db.execute_query(query, (username, password_hash))
        return result[0][0] if result else None
