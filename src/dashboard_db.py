"""
DSB Tournament · 仪表盘配置模块
存储页面所有可编辑内容，直接改数据库就能改页面
"""
import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

# 默认配置 — 零基础也能一键恢复
DEFAULT_CONTENT = {
    # === 首页 (main.html) ===
    "site_title": "星际争霸2 第一届DSB月赛杯",
    "site_subtitle": "赛事章程 (2026赛季5月)",
    "hero_banner_bg": "image/hero-banner.png",
    "hero_banner_height": "400px",
    
    # 赛事概况
    "tournament_name": "星际争霸2 DSB月赛杯",
    "game_version": "《星际争霸2》国服最新版本",
    "game_server": "国服",
    "game_mode": "1v1 自定义游戏房间（开启官方观战Mod）",
    "max_players": "24人",
    "prize_pool": "800元人民币",
    
    # 报名截止
    "reg_deadline": "2026年5月20日",
    "swiss_start": "5月20日 — 5月27日 14:00",
    "bracket_start": "5月30日 — 5月31日",
    
    # 奖金分配
    "prize_1st": "150元",
    "prize_2nd": "90元",
    "prize_3rd": "70元",
    "prize_4th": "50元",
    "prize_5_8": "30元",
    "prize_9_24": "20元",
    "prize_total": "800",
    
    # 颜色主题
    "theme_bg": "#0b0c10",
    "theme_container": "#1f2833",
    "theme_text": "#c5c6c7",
    "theme_title": "#ffffff",
    "theme_accent": "#66fcf1",
    "theme_accent_dim": "#45a29e",
    "theme_gold": "#f4d03f",
    
    # 联系信息
    "contact_info": "GL HF | DSB Tournament © 2026 联系群聊:701237203",
    
    # 赛程表 - 瑞士轮时间
    "round1_start": "5月20日 00:00",
    "round1_end": "5月21日 14:00",
    "round2_start": "5月21日 14:00",
    "round2_end": "5月23日 02:00",
    "round3_start": "5月23日 02:00",
    "round3_end": "5月24日 14:00",
    "round4_start": "5月24日 14:00",
    "round4_end": "5月26日 02:00",
    "round5_start": "5月26日 02:00",
    "round5_end": "5月27日 14:00",
}

def init_dashboard_table():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # 写入默认值
    now = datetime.now().isoformat()
    for k, v in DEFAULT_CONTENT.items():
        conn.execute(
            "INSERT OR IGNORE INTO content_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (k, v, now)
        )
    conn.commit()
    conn.close()

def get_all_content() -> dict:
    conn = _conn()
    rows = conn.execute("SELECT key, value FROM content_settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def update_content(key: str, value: str):
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO content_settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, now)
    )
    conn.commit()
    conn.close()

def update_content_batch(items: dict):
    conn = _conn()
    now = datetime.now().isoformat()
    for k, v in items.items():
        conn.execute(
            "INSERT OR REPLACE INTO content_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (k, str(v), now)
        )
    conn.commit()
    conn.close()

def reset_content():
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM content_settings")
    for k, v in DEFAULT_CONTENT.items():
        conn.execute(
            "INSERT INTO content_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (k, v, now)
        )
    conn.commit()
    conn.close()

# 启动时初始化
init_dashboard_table()
