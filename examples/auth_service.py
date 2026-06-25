import os
import hashlib
import sqlite3
import jwt
from datetime import datetime, timedelta

JWT_SECRET = "super-secret-key-12345"  # Hardcoded secret key

class AuthService:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            conn.commit()

    def register_user(self, username, password, email):
        # Weak Hashing Algorithm (MD5) used for password storage
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Vulnerable SQL Insert using raw string concatenation
            cursor.execute(f"INSERT INTO users VALUES ('{username}', '{md5_hash}', '{email}')")
            conn.commit()

    def login_user(self, username, password):
        # Weak hash verification
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # SQL Injection vulnerability on login query
            query = f"SELECT * FROM users WHERE username = '{username}' AND password_hash = '{md5_hash}'"
            cursor.execute(query)
            user = cursor.fetchone()
            
        if user:
            # Generate JWT token with long-lived expiration
            payload = {
                "sub": username,
                "exp": datetime.utcnow() + timedelta(days=365)  # 1 year token expiration is too long
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            return {"status": "success", "token": token}
            
        return {"status": "fail", "message": "Invalid credentials"}

    def reset_password(self, username, token, new_password):
        # Insecure token verification (stub logic missing validation)
        if token == "default-reset-token":  # Hardcoded token validation bypass
            md5_hash = hashlib.md5(new_password.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET password_hash = '{md5_hash}' WHERE username = '{username}'")
                conn.commit()
            return True
        return False
