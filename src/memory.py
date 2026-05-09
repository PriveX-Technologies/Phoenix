import sqlite3
import os
import json
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/phoenix_memory.db")


# ── Database setup ────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                turn        INTEGER NOT NULL,
                user_text   TEXT NOT NULL,
                bot_text    TEXT NOT NULL,
                emotion     TEXT DEFAULT 'neutral',
                approved    INTEGER DEFAULT 1,
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key         TEXT NOT NULL UNIQUE,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                started_at  TEXT NOT NULL,
                turn_count  INTEGER DEFAULT 0
            );
        """)


# ── Session management ────────────────────────────────────────────────────────

def new_session() -> str:
    """Create a new session ID and register it."""
    session_id = datetime.now().strftime("sess_%Y%m%d_%H%M%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, started_at) VALUES (?, ?)",
            (session_id, datetime.now().isoformat())
        )
    return session_id


def increment_turn(session_id: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET turn_count = turn_count + 1 WHERE id = ?",
            (session_id,)
        )


# ── Conversation storage ──────────────────────────────────────────────────────

def save_turn(session_id: str, turn: int, user_text: str, bot_text: str,
              emotion: str = "neutral", approved: bool = True):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO conversations
                (session_id, turn, user_text, bot_text, emotion, approved, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, turn, user_text, bot_text,
            emotion, int(approved), datetime.now().isoformat()
        ))
    increment_turn(session_id)


def get_recent_turns(n: int = 10, session_id: str = None) -> list[dict]:

    with get_conn() as conn:
        if session_id:
            rows = conn.execute("""
                SELECT user_text, bot_text, emotion, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
            """, (session_id, n)).fetchall()
        else:
            rows = conn.execute("""
                SELECT user_text, bot_text, emotion, timestamp
                FROM conversations
                ORDER BY id DESC LIMIT ?
            """, (n,)).fetchall()

    return [dict(r) for r in reversed(rows)]


def build_context_string(n: int = 5, session_id: str = None) -> str:

    turns = get_recent_turns(n, session_id)
    parts = []
    for t in turns:
        parts.append(t["user_text"])
        parts.append(t["bot_text"])
    return " ".join(parts)


# ── Fact extraction & storage ─────────────────────────────────────────────────

FACT_PATTERNS = [
    (r"\bmy name is (\w+)", "name"),
    (r"\bi am (\w+)", "name"),
    (r"\bi('m| am) (\d+) years? old", "age"),
    (r"\bi live in ([\w\s]+)", "location"),
    (r"\bi('m| am) from ([\w\s]+)", "location"),
    (r"\bi work (at|for|as) ([\w\s]+)", "job"),
    (r"\bmy (favourite|favorite) ([\w]+) is ([\w\s]+)", None),  # dynamic key
    (r"\bi like ([\w\s]+)", "likes"),
    (r"\bi (hate|dislike) ([\w\s]+)", "dislikes"),
]


def extract_and_save_facts(text: str) -> dict:
    """Extract facts from user text and persist them. Returns extracted facts."""
    text_lower = text.lower().strip()
    found = {}

    for pattern, key in FACT_PATTERNS:
        match = re.search(pattern, text_lower)
        if not match:
            continue

        if key == "name":
            value = match.group(match.lastindex).strip()
            # ignore common false positives
            if value in {"a", "an", "the", "not", "just", "so", "very"}:
                continue
            found["name"] = value

        elif key == "age":
            found["age"] = match.group(2).strip()

        elif key == "location":
            found["location"] = match.group(match.lastindex).strip()

        elif key == "job":
            found["job"] = match.group(2).strip()

        elif key is None:
            # dynamic: "my favourite X is Y"
            category = match.group(2)
            value    = match.group(3).strip()
            found[f"favourite_{category}"] = value

        elif key == "likes":
            found["likes"] = match.group(1).strip()

        elif key == "dislikes":
            found["dislikes"] = match.group(2).strip()

    if found:
        save_facts(found)

    return found


def save_facts(facts: dict):
    """Upsert facts into the database."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        for k, v in facts.items():
            conn.execute("""
                INSERT INTO facts (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (k, v, now))


def get_all_facts() -> dict:
    """Retrieve all stored facts as a dict."""
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM facts").fetchall()
    return {r["key"]: r["value"] for r in rows}


def build_profile_string() -> str:
    """Build a compact profile string for model context injection."""
    facts = get_all_facts()
    if not facts:
        return ""
    parts = []
    if "name" in facts:
        parts.append(f"user name is {facts['name']}")
    if "age" in facts:
        parts.append(f"user is {facts['age']} years old")
    if "location" in facts:
        parts.append(f"user lives in {facts['location']}")
    if "job" in facts:
        parts.append(f"user works as {facts['job']}")
    for k, v in facts.items():
        if k.startswith("favourite_"):
            parts.append(f"{k.replace('_', ' ')} is {v}")
    return " ".join(parts)


# ── Stats ─────────────────────────────────────────────────────────────────────

def memory_stats() -> dict:
    with get_conn() as conn:
        total_turns = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        total_facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        sessions    = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    return {
        "total_turns": total_turns,
        "total_facts": total_facts,
        "sessions":    sessions,
    }


def clear_session_memory(session_id: str):
    """Delete all turns from a specific session (keeps facts)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))


def clear_all_facts():
    """Wipe all stored facts."""
    with get_conn() as conn:
        conn.execute("DELETE FROM facts")


# ── Init on import ────────────────────────────────────────────────────────────
init_db()


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sid = new_session()
    print(f"Session: {sid}")

    extract_and_save_facts("my name is Alex")
    extract_and_save_facts("i am 25 years old")
    extract_and_save_facts("i live in London")
    extract_and_save_facts("my favourite colour is blue")

    print("Facts:", get_all_facts())
    print("Profile string:", build_profile_string())

    save_turn(sid, 1, "hello there", "hi how are you", emotion="happy")
    save_turn(sid, 2, "i feel sad", "i'm sorry to hear that", emotion="sad")

    print("Recent turns:", get_recent_turns(5))
    print("Context string:", build_context_string(3))
    print("Stats:", memory_stats())