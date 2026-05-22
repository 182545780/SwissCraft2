"""
DSB 月赛杯 — 录像管理数据库模块
表结构:
  videos: 录像文件表
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "..", "videos")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_videos():
    """初始化录像表。"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT NOT NULL,
            original_name TEXT NOT NULL,
            uploader    TEXT NOT NULL DEFAULT '',
            upload_time TEXT NOT NULL,
            file_size   INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT ''
        );
    """)
    conn.commit()
    conn.close()

    # 确保存储目录存在
    os.makedirs(VIDEOS_DIR, exist_ok=True)


def get_all_videos() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, original_name, uploader, upload_time, file_size, description "
        "FROM videos ORDER BY upload_time DESC"
    ).fetchall()
    conn.close()
    videos = []
    for r in rows:
        d = dict(r)
        # 从 filename 中提取文件夹名，如 "瑞士轮r1/xxx.SC2Replay" -> "瑞士轮r1"
        folder = ""
        if "/" in d["filename"]:
            folder = d["filename"].rsplit("/", 1)[0]
        d["folder"] = folder
        videos.append(d)
    return videos


def get_video(video_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, filename, original_name, uploader, upload_time, file_size, description "
        "FROM videos WHERE id=?",
        (video_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_video(filename: str, original_name: str, uploader: str, file_size: int, description: str = "") -> int:
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO videos (filename, original_name, uploader, upload_time, file_size, description) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (filename, original_name, uploader, now, file_size, description),
    )
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return vid


def delete_video(video_id: int) -> bool:
    """删除录像记录和文件。返回是否成功。"""
    video = get_video(video_id)
    if not video:
        return False

    # 删除文件
    filepath = os.path.join(VIDEOS_DIR, video["filename"])
    if os.path.exists(filepath):
        os.remove(filepath)

    # 删除记录
    conn = get_conn()
    conn.execute("DELETE FROM videos WHERE id=?", (video_id,))
    conn.commit()
    conn.close()
    return True


# 自动初始化
init_videos()
