"""
DSB 瑞士轮 — SQLite 数据库模块
表结构:
  players: 选手表
  matches: 比赛记录表
  state:   全局状态 (当前轮次)
"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

# ---------- 选手种子数据 (从 config.json 读取) ----------
import json, os
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except:
    CONFIG = {}

SEED_PLAYERS = CONFIG.get("seed_players", [])
# 兼容旧格式：如果 seed_players 是空数组，但想保留默认选手就加个标志
if not SEED_PLAYERS and CONFIG.get("use_default_seeds", True):
    SEED_PLAYERS = []  # 默认为空，从仪表盘添加选手

import json, os
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
def _get_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
TOTAL_ROUNDS = _get_config().get("total_rounds", 5)


def get_conn() -> sqlite3.Connection:
    """获取数据库连接，启用 WAL 模式和外键约束。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化表结构并写入种子数据（如不存在）。"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id    INTEGER PRIMARY KEY,
            name  TEXT NOT NULL,
            mmr   INTEGER NOT NULL,
            race  TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS matches (
            id         TEXT PRIMARY KEY,
            round      INTEGER NOT NULL,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER NOT NULL,
            winner_id  INTEGER,
            FOREIGN KEY (player1_id) REFERENCES players(id),
            FOREIGN KEY (player2_id) REFERENCES players(id),
            FOREIGN KEY (winner_id)  REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # 迁移：旧表可能没有 race 列
    try:
        conn.execute("ALTER TABLE players ADD COLUMN race TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 种子选手 (如表中无数据则写入)
    existing = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if existing == 0:
        conn.executemany(
            "INSERT INTO players (id, name, mmr, race) VALUES (?, ?, ?, ?)",
            SEED_PLAYERS,
        )

    # 初始化轮次状态
    cur = conn.execute("SELECT value FROM state WHERE key='current_round'").fetchone()
    if cur is None:
        conn.execute("INSERT INTO state (key, value) VALUES ('current_round', '0')")

    conn.commit()
    conn.close()


# ---------- 选手 ----------
def get_all_players() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT id, name, mmr, race FROM players ORDER BY mmr DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- 轮次 ----------
def get_current_round() -> int:
    conn = get_conn()
    row = conn.execute("SELECT value FROM state WHERE key='current_round'").fetchone()
    conn.close()
    return int(row["value"]) if row else 0


def set_current_round(round_num: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO state (key, value) VALUES ('current_round', ?)",
        (str(round_num),),
    )
    conn.commit()
    conn.close()


# ---------- 比赛 ----------
def get_matches_by_round(round_num: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, round, player1_id, player2_id, winner_id FROM matches WHERE round=? ORDER BY id",
        (round_num,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_matches() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, round, player1_id, player2_id, winner_id FROM matches ORDER BY round, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_matches(matches: list[dict]):
    """批量插入比赛记录。每条: {id, round, player1_id, player2_id, winner_id}"""
    conn = get_conn()
    conn.executemany(
        "INSERT INTO matches (id, round, player1_id, player2_id, winner_id) VALUES (?,?,?,?,?)",
        [(m["id"], m["round"], m["player1_id"], m["player2_id"], m["winner_id"]) for m in matches],
    )
    conn.commit()
    conn.close()


def set_winner(match_id: str, winner_id: int):
    conn = get_conn()
    conn.execute("UPDATE matches SET winner_id=? WHERE id=?", (winner_id, match_id))
    conn.commit()
    conn.close()


def clear_winner(match_id: str):
    """撤销比赛结果 — 将 winner_id 置空，保留配对记录。"""
    conn = get_conn()
    conn.execute("UPDATE matches SET winner_id=NULL WHERE id=?", (match_id,))
    conn.commit()
    conn.close()


def delete_match(match_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM matches WHERE id=?", (match_id,))
    conn.commit()
    conn.close()


def clear_all_matches():
    conn = get_conn()
    conn.execute("DELETE FROM matches")
    conn.execute("UPDATE state SET value='0' WHERE key='current_round'")
    conn.commit()
    conn.close()


# 自动初始化
init_db()
