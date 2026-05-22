"""
DSB 月赛杯 · 八强淘汰赛模块
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_bracket_table():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bracket_matches (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            slot       TEXT NOT NULL UNIQUE,  -- qf1~qf4, sf1~sf2, final, third
            round      TEXT NOT NULL,          -- quarterfinal, semifinal, final, third_place
            player1_id INTEGER,
            player2_id INTEGER,
            winner_id  INTEGER,
            score1     INTEGER DEFAULT 0,
            score2     INTEGER DEFAULT 0,
            status     TEXT DEFAULT 'pending', -- pending, active, completed
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def get_bracket():
    conn = _conn()
    rows = conn.execute("SELECT * FROM bracket_matches ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_bracket(top8: list[dict]):
    """生成八强对阵，top8按排名传入 [(id,name,mmr,race), ...]"""
    conn = _conn()
    conn.execute("DELETE FROM bracket_matches")
    
    pairings = [
        ("qf1", "quarterfinal", top8[0]["id"], top8[7]["id"]),  # 1 vs 8
        ("qf2", "quarterfinal", top8[3]["id"], top8[4]["id"]),  # 4 vs 5
        ("qf3", "quarterfinal", top8[1]["id"], top8[6]["id"]),  # 2 vs 7
        ("qf4", "quarterfinal", top8[2]["id"], top8[5]["id"]),  # 3 vs 6
        ("sf1", "semifinal", None, None),    # qf1胜者 vs qf2胜者
        ("sf2", "semifinal", None, None),    # qf3胜者 vs qf4胜者
        ("third", "third_place", None, None), # sf1败者 vs sf2败者
        ("final", "final", None, None),       # sf1胜者 vs sf2胜者
    ]
    
    for slot, round_name, p1, p2 in pairings:
        conn.execute(
            "INSERT INTO bracket_matches (slot, round, player1_id, player2_id) VALUES (?, ?, ?, ?)",
            (slot, round_name, p1, p2),
        )
    
    conn.commit()
    conn.close()


def set_bracket_result(slot: str, winner_id: int, score1: int, score2: int):
    """记录一场淘汰赛结果，自动晋级胜者到下一轮"""
    conn = _conn()
    
    # 更新当前比赛
    match = conn.execute("SELECT * FROM bracket_matches WHERE slot=?", (slot,)).fetchone()
    if not match:
        conn.close()
        return False
    
    loser_id = match["player1_id"] if match["player2_id"] == winner_id else match["player2_id"]
    
    conn.execute(
        "UPDATE bracket_matches SET winner_id=?, score1=?, score2=?, status='completed' WHERE slot=?",
        (winner_id, score1, score2, slot),
    )
    
    # 晋级逻辑
    advance_map = {
        "qf1": "sf1", "qf2": "sf1",
        "qf3": "sf2", "qf4": "sf2",
    }
    
    if slot in advance_map:
        next_slot = advance_map[slot]
        # 检查同一半区的另一场是否也完成了
        partner = "qf2" if slot == "qf1" else ("qf1" if slot == "qf2" else ("qf4" if slot == "qf3" else "qf3"))
        partner_match = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot=?", (partner,)).fetchone()
        
        if partner_match and partner_match["winner_id"]:
            # 两场都完成了，更新半决赛对阵
            if slot in ("qf1", "qf2"):
                w1 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='qf1'").fetchone()["winner_id"]
                w2 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='qf2'").fetchone()["winner_id"]
                conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='sf1'", (w1, w2))
            else:
                w1 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='qf3'").fetchone()["winner_id"]
                w2 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='qf4'").fetchone()["winner_id"]
                conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='sf2'", (w1, w2))
    
    # 半决赛晋级到决赛/季军赛
    if slot == "sf1":
        sf2 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='sf2'").fetchone()
        sf2_loser = conn.execute("SELECT player1_id, player2_id, winner_id FROM bracket_matches WHERE slot='sf2'").fetchone()
        if sf2 and sf2["winner_id"]:
            conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='final'",
                        (winner_id, sf2["winner_id"]))
        if sf2_loser and sf2_loser["winner_id"]:
            l1 = sf2_loser["player1_id"] if sf2_loser["player2_id"] == sf2_loser["winner_id"] else sf2_loser["player2_id"]
            conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='third'",
                        (loser_id, l1))
    
    if slot == "sf2":
        sf1 = conn.execute("SELECT winner_id FROM bracket_matches WHERE slot='sf1'").fetchone()
        if sf1 and sf1["winner_id"]:
            conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='final'",
                        (sf1["winner_id"], winner_id))
            # 季军赛：sf1败者 vs sf2败者
            sf1_match = conn.execute("SELECT player1_id, player2_id, winner_id FROM bracket_matches WHERE slot='sf1'").fetchone()
            if sf1_match and sf1_match["winner_id"]:
                l2 = sf1_match["player1_id"] if sf1_match["player2_id"] == sf1_match["winner_id"] else sf1_match["player2_id"]
                conn.execute("UPDATE bracket_matches SET player1_id=?, player2_id=? WHERE slot='third'",
                            (l2, loser_id))
    
    conn.commit()
    conn.close()
    return True


def reset_bracket():
    conn = _conn()
    conn.execute("DELETE FROM bracket_matches")
    conn.commit()
    conn.close()


# 初始化
init_bracket_table()
