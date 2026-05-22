"""
DSB 月赛杯 · 报名管理模块
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_registration_table():
    """初始化报名相关表"""
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS registration_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            mmr        INTEGER NOT NULL DEFAULT 0,
            race       TEXT NOT NULL DEFAULT '',
            comment    TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'pending'
        );
    """)
    # 默认配置
    defaults = [
        ("open", "false"),
        ("title", "DSB月赛杯报名"),
        ("max_slots", "24"),
        ("description", "请填写真实信息"),
    ]
    for k, v in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO registration_config (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


def get_config() -> dict:
    conn = _conn()
    rows = conn.execute("SELECT key, value FROM registration_config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(key: str, value: str):
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO registration_config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_registrations() -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        "SELECT id, name, mmr, race, comment, created_at, status "
        "FROM registrations ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_registration(name: str, mmr: int, race: str, comment: str) -> dict:
    conn = _conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO registrations (name, mmr, race, comment, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, mmr, race, comment, now),
    )
    conn.commit()
    rid = cur.lastrowid
    row = conn.execute("SELECT * FROM registrations WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(row)


def delete_registration(rid: int):
    conn = _conn()
    conn.execute("DELETE FROM registrations WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def count_registrations() -> int:
    conn = _conn()
    cnt = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    conn.close()
    return cnt


# 初始化
init_registration_table()
