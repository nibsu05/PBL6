"""Account and expiring sessions for the loopback-only station app."""

from collections import deque
from contextlib import closing
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
import re
import secrets
import sqlite3
from threading import Lock
import time


PASSWORD_ROUNDS = 600_000
SESSION_SECONDS = 8 * 60 * 60
COOKIE_NAME = 'pbl6_station_session'


class AccountExists(Exception):
    pass


def password_digest(password, salt, rounds=PASSWORD_ROUNDS):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds)


class Accounts:
    def __init__(self, path):
        self.path = path
        self.lock = Lock()
        self.recent_attempts = deque()
        self.sessions = {}
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS owner (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    username TEXT NOT NULL,
                    salt BLOB NOT NULL,
                    password_digest BLOB NOT NULL,
                    rounds INTEGER NOT NULL
                )
            ''')

    def owner(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute('SELECT username, salt, password_digest, rounds FROM owner WHERE id = 1').fetchone()

    def begin_attempt(self):
        now = time.monotonic()
        with self.lock:
            while self.recent_attempts and self.recent_attempts[0] < now - 60:
                self.recent_attempts.popleft()
            if len(self.recent_attempts) >= 6:
                return False
            self.recent_attempts.append(now)
            return True

    def register(self, username, password):
        if not re.fullmatch(r'\w[\w.-]{2,31}', username):
            raise ValueError('invalid_username')
        if len(password) < 12:
            raise ValueError('weak_password')
        if self.owner() is not None:
            raise AccountExists
        salt = secrets.token_bytes(16)
        digest = password_digest(password, salt)
        try:
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute('INSERT INTO owner VALUES (1, ?, ?, ?, ?)',
                           (username, salt, digest, PASSWORD_ROUNDS))
        except sqlite3.IntegrityError as error:
            raise AccountExists from error
        return self.open_session(username)

    def sign_in(self, username, password):
        row = self.owner()
        if row is None:
            return None
        stored_name, salt, expected, rounds = row
        same_password = hmac.compare_digest(expected, password_digest(password, salt, rounds))
        if same_password and stored_name.casefold() == username.casefold():
            return self.open_session(stored_name)
        return None

    @staticmethod
    def token_key(cookie_header):
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header or '')
        except CookieError:
            return None
        entry = cookie.get(COOKIE_NAME)
        if entry is None or not re.fullmatch(r'[A-Za-z0-9_-]{43}', entry.value):
            return None
        return hashlib.sha256(entry.value.encode('ascii')).digest()

    def open_session(self, username):
        token = secrets.token_urlsafe(32)
        key = hashlib.sha256(token.encode('ascii')).digest()
        now = time.monotonic()
        with self.lock:
            self.sessions = {key: session for key, session in self.sessions.items() if session[1] > now}
            self.sessions[key] = (username, now + SESSION_SECONDS)
            self.recent_attempts.clear()
        return f'{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}'

    def session_user(self, cookie_header):
        key = self.token_key(cookie_header)
        with self.lock:
            session = self.sessions.get(key)
            if session is not None and session[1] > time.monotonic():
                return session[0]
            self.sessions.pop(key, None)
        return None

    def close_session(self, cookie_header):
        with self.lock:
            self.sessions.pop(self.token_key(cookie_header), None)
        return f'{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
