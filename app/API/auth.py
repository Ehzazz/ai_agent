import os
import json
import uuid
import secrets
import hashlib
from typing import Dict, List
import asyncio

# In-memory stores
USERS: Dict[str, Dict] = {}  # user_id -> {username, password_hash, history}
USERNAME_INDEX: Dict[str, str] = {}  # username.lower() -> user_id
ACTIVE_SESSIONS: Dict[str, str] = {}  # session_token -> user_id

# Current session tracking (like ChatGPT)
CURRENT_SESSION_TOKEN: str = ""
CURRENT_SESSION_USER_ID: str = ""

# ----------------------------
# Utilities
# ----------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------------------
# Auth & Session
# ----------------------------

def create_user(username: str, password: str) -> str:
    username_key = username.strip().lower()
    if username_key in USERNAME_INDEX:
        return "❌ Username already exists. Please choose a different one."

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    password_hash = hash_password(password)

    USERS[user_id] = {
        "username": username,
        "password_hash": password_hash,
        "history": []
    }
    USERNAME_INDEX[username_key] = user_id

    save_data()
    return f"✅ User created successfully! Your user ID is: {user_id}"

def login_user(username: str, password: str) -> str:
    global CURRENT_SESSION_TOKEN, CURRENT_SESSION_USER_ID

    username_key = username.strip().lower()
    user_id = USERNAME_INDEX.get(username_key)

    if not user_id:
        return "❌ Username not found."

    stored_hash = USERS[user_id]["password_hash"]
    if hash_password(password) != stored_hash:
        return "❌ Incorrect password."

    session_token = secrets.token_hex(16)
    ACTIVE_SESSIONS[session_token] = user_id
    CURRENT_SESSION_TOKEN = session_token
    CURRENT_SESSION_USER_ID = user_id

    return f"✅ Login successful! Welcome, {username}"

def logout_user(session_token: str) -> str:
    global CURRENT_SESSION_TOKEN, CURRENT_SESSION_USER_ID
    if session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
        if session_token == CURRENT_SESSION_TOKEN:
            CURRENT_SESSION_TOKEN = ""
            CURRENT_SESSION_USER_ID = ""
        return "✅ Successfully logged out."
    return "⚠️ Invalid or expired session token."

# ----------------------------
# Helpers
# ----------------------------

def get_user_id_from_session(session_token: str) -> str:
    return ACTIVE_SESSIONS.get(session_token, "")

def get_history_by_user_id(user_id: str) -> List[Dict[str, str]]:
    return USERS.get(user_id, {}).get("history", [])

def get_history(session_token: str) -> List[Dict[str, str]]:
    user_id = get_user_id_from_session(session_token)
    return get_history_by_user_id(user_id) if user_id else []

# ----------------------------
# Persistence
# ----------------------------

DATA_FILE = os.path.join(os.path.dirname(__file__), "user_data.json")

def save_data():
    data = {
        "users": USERS,
        "username_index": USERNAME_INDEX
    }
    print(f"[DEBUG] Saving data to {DATA_FILE}:\n{data}")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_data():
    global USERS, USERNAME_INDEX
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            USERS.update(data.get("users", {}))
            USERNAME_INDEX.update(data.get("username_index", {}))
