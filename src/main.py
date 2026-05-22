"""
DSB 月赛杯 · 瑞士轮 — FastAPI 后端
提供 REST API + 静态文件服务 + 录像管理
"""

import random
import os
import sys
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

# 确保同目录模块可导入 (database, models, dsb_videos)
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ---------- 管理员密码 ----------
ADMIN_PASSWORD = os.getenv("DSB_ADMIN_PASSWORD", "dsb2026")


def verify_admin(x_admin_password: str = Header(None)):
    """验证管理员密码，保护写操作。"""
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(401, "管理员密码错误 — 请在页面顶部点击解锁按钮")


def verify_admin_or_none(x_admin_password: str = Header(None)):
    """验证管理员密码，若未提供则返回 False 而非报错。"""
    return x_admin_password == ADMIN_PASSWORD

from database import (
    get_all_players, get_all_matches, get_matches_by_round,
    get_current_round, set_current_round,
    insert_matches, set_winner, clear_winner, delete_match, clear_all_matches,
    TOTAL_ROUNDS, DB_PATH,
)
from models import StateOut, PlayerOut, MatchOut, StandingEntry, BaseModel
from dsb_videos import (
    get_all_videos, get_video, insert_video, delete_video,
    VIDEOS_DIR,
)


# ---------- 启动事件 ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库在 import database / dsb_videos 时已自动初始化
    yield


app = FastAPI(title="DSB 瑞士轮", lifespan=lifespan)

# ---------- 静态文件 ----------
BISAI_DIR = os.path.join(os.path.dirname(__file__), "..", "bisai")

@app.get("/")
async def root():
    return FileResponse(os.path.join(BISAI_DIR, "main.html"))


@app.get("/saicheng")
async def saicheng():
    return FileResponse(os.path.join(BISAI_DIR, "saicheng.html"))


@app.get("/videos")
async def videos_page():
    return FileResponse(os.path.join(BISAI_DIR, "videos.html"))


# 直接挂载 bisai 目录中的静态资源 (CSS/JS/图片等)
if os.path.isdir(BISAI_DIR):
    app.mount("/bisai", StaticFiles(directory=BISAI_DIR), name="bisai_static")

# 挂载地图图片目录
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "image")
if os.path.isdir(IMAGE_DIR):
    app.mount("/image", StaticFiles(directory=IMAGE_DIR), name="image_static")


# ========================================
# 瑞士轮配对算法 (保持不变)
# ========================================

def has_played(all_matches: list[dict], p1_id: int, p2_id: int) -> bool:
    opponents: dict[int, set[int]] = defaultdict(set)
    for m in all_matches:
        if m["winner_id"] is not None:
            opponents[m["player1_id"]].add(m["player2_id"])
            opponents[m["player2_id"]].add(m["player1_id"])
    return p2_id in opponents.get(p1_id, set())


def get_player_wins(all_matches: list[dict], player_id: int) -> int:
    return sum(1 for m in all_matches if m["winner_id"] == player_id)


def generate_pairings(players: list[dict], all_matches: list[dict], round_num: int) -> list[dict]:
    if round_num == 1:
        shuffled = players[:]
        random.shuffle(shuffled)
        pairs = []
        for i in range(0, len(shuffled), 2):
            if i + 1 < len(shuffled):
                pairs.append({
                    "id": f"r{round_num}-{i//2}",
                    "round": round_num,
                    "player1_id": shuffled[i]["id"],
                    "player2_id": shuffled[i + 1]["id"],
                    "winner_id": None,
                })
        return pairs

    groups: dict[int, list[dict]] = defaultdict(list)
    for p in players:
        w = get_player_wins(all_matches, p["id"])
        groups[w].append(p)

    new_pairs: list[dict] = []
    unpaired: list[dict] = []

    sorted_wins = sorted(groups.keys(), reverse=True)
    for wins in sorted_wins:
        group = unpaired + groups[wins]
        unpaired = []
        random.shuffle(group)

        used = [False] * len(group)
        for i in range(len(group)):
            if used[i]:
                continue
            found = False
            for j in range(i + 1, len(group)):
                if used[j]:
                    continue
                if not has_played(all_matches, group[i]["id"], group[j]["id"]):
                    new_pairs.append({
                        "id": f"r{round_num}-{len(new_pairs)}",
                        "round": round_num,
                        "player1_id": group[i]["id"],
                        "player2_id": group[j]["id"],
                        "winner_id": None,
                    })
                    used[i] = used[j] = True
                    found = True
                    break
            if not found:
                used[i] = True
                unpaired.append(group[i])

    for i in range(0, len(unpaired), 2):
        if i + 1 < len(unpaired):
            new_pairs.append({
                "id": f"r{round_num}-extra-{i // 2}",
                "round": round_num,
                "player1_id": unpaired[i]["id"],
                "player2_id": unpaired[i + 1]["id"],
                "winner_id": None,
            })

    return new_pairs


def compute_standings(players: list[dict], all_matches: list[dict]) -> list[dict]:
    wins_map: dict[int, int] = defaultdict(int)
    opponents_map: dict[int, set[int]] = defaultdict(set)

    for m in all_matches:
        if m["winner_id"] is None:
            continue
        loser_id = m["player1_id"] if m["winner_id"] == m["player2_id"] else m["player2_id"]
        wins_map[m["winner_id"]] += 1
        opponents_map[m["player1_id"]].add(m["player2_id"])
        opponents_map[m["player2_id"]].add(m["player1_id"])

    ranked = []
    for p in players:
        wins = wins_map.get(p["id"], 0)
        opp_score = sum(wins_map.get(opp, 0) for opp in opponents_map.get(p["id"], set()))
        ranked.append({
            "id": p["id"],
            "name": p["name"],
            "mmr": p["mmr"],
            "race": p.get("race", ""),
            "wins": wins,
            "opponent_score": opp_score,
            "games_won": wins,
        })

    ranked.sort(key=lambda x: (-x["wins"], -x["opponent_score"], -x["mmr"]))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1

    return ranked


# ========================================
# 瑞士轮 API (保持不变)
# ========================================

@app.get("/api/state", response_model=StateOut)
def get_state():
    players_raw = get_all_players()
    current_round = get_current_round()
    all_matches = get_all_matches()
    pairings_raw = get_matches_by_round(current_round) if current_round > 0 else []
    standings_raw = compute_standings(players_raw, all_matches)
    round_complete = len(pairings_raw) > 0 and all(m["winner_id"] is not None for m in pairings_raw)
    finished = current_round >= TOTAL_ROUNDS and round_complete

    return StateOut(
        current_round=current_round,
        total_rounds=TOTAL_ROUNDS,
        players=[PlayerOut(**p) for p in players_raw],
        pairings=[MatchOut(**m) for m in pairings_raw],
        standings=[StandingEntry(**s) for s in standings_raw],
        round_complete=round_complete,
        finished=finished,
    )


class AuthBody(BaseModel):
    password: str

@app.post("/api/auth")
def auth(body: AuthBody):
    if body.password != ADMIN_PASSWORD:
        raise HTTPException(401, "密码错误")
    return {"ok": True, "token": ADMIN_PASSWORD}


@app.post("/api/next-round")
def next_round(_: None = Depends(verify_admin)):
    current_round = get_current_round()
    if current_round >= TOTAL_ROUNDS:
        return get_state()
    players = get_all_players()
    if current_round > 0:
        existing = get_matches_by_round(current_round)
        for m in existing:
            if m["winner_id"] is not None:
                existing_ids = {x["id"] for x in get_all_matches()}
                if m["id"] not in existing_ids:
                    insert_matches([{
                        "id": m["id"], "round": m["round"],
                        "player1_id": m["player1_id"], "player2_id": m["player2_id"],
                        "winner_id": m["winner_id"],
                    }])
    new_round = current_round + 1
    if new_round > TOTAL_ROUNDS:
        return get_state()
    set_current_round(new_round)
    all_matches = get_all_matches()
    pairs = generate_pairings(players, all_matches, new_round)
    if pairs:
        insert_matches(pairs)
    return get_state()


@app.post("/api/record-result/{match_id}")
def record_result(match_id: str, winner_id: int, _: None = Depends(verify_admin)):
    all_matches = get_all_matches()
    target = next((m for m in all_matches if m["id"] == match_id), None)
    if target is None:
        raise HTTPException(404, "比赛记录不存在")
    if target["winner_id"] is not None:
        raise HTTPException(409, "该场次已记录结果")
    if winner_id not in (target["player1_id"], target["player2_id"]):
        raise HTTPException(400, "胜者ID不在该场比赛选手中")
    set_winner(match_id, winner_id)
    return get_state()


@app.post("/api/undo-result/{match_id}")
def undo_result(match_id: str, _: None = Depends(verify_admin)):
    all_matches = get_all_matches()
    target = next((m for m in all_matches if m["id"] == match_id), None)
    if target is None:
        raise HTTPException(404, "比赛记录不存在")
    clear_winner(match_id)
    return get_state()


@app.post("/api/reset")
def reset_all(_: None = Depends(verify_admin)):
    clear_all_matches()
    return get_state()


# ========================================
# 录像管理 API
# ========================================

@app.get("/api/videos")
def list_videos():
    """获取录像列表 — 所有人可访问。"""
    videos = get_all_videos()
    return {"videos": videos}


@app.post("/api/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    description: str = Form(""),
    uploader: str = Form(""),
    x_admin_password: str = Header(None),
):
    """上传录像文件 — 需要管理员密码。"""
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(401, "管理员密码错误")

    # 生成唯一文件名
    ext = os.path.splitext(file.filename or "replay.SC2Replay")[1] or ".SC2Replay"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(VIDEOS_DIR, unique_name)

    # 保存文件
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 写入数据库
    vid = insert_video(
        filename=unique_name,
        original_name=file.filename or "unknown",
        uploader=uploader or "管理员",
        file_size=len(content),
        description=description,
    )

    return {"ok": True, "video_id": vid, "filename": unique_name}


@app.get("/api/videos/{video_id}/download")
def download_video(video_id: int):
    """下载录像文件 — 所有人可访问。"""
    video = get_video(video_id)
    if not video:
        raise HTTPException(404, "录像不存在")

    filepath = os.path.join(VIDEOS_DIR, video["filename"])
    if not os.path.exists(filepath):
        raise HTTPException(404, "录像文件丢失")

    return FileResponse(
        filepath,
        media_type="application/octet-stream",
        filename=video["original_name"],
    )


@app.delete("/api/videos/{video_id}")
def remove_video(video_id: int, _: None = Depends(verify_admin)):
    """删除录像 — 需要管理员密码。"""
    ok = delete_video(video_id)
    if not ok:
        raise HTTPException(404, "录像不存在")
    return {"ok": True}


# ========================================
# 报名管理 API
# ========================================
from registration import (
    get_config as get_reg_config,
    set_config as set_reg_config,
    get_registrations,
    add_registration,
    delete_registration,
    count_registrations,
)

@app.get("/api/register/config")
def api_reg_config():
    """获取报名配置"""
    return get_reg_config()


class ConfigBody(BaseModel):
    key: str
    value: str

@app.post("/api/register/config")
def api_update_reg_config(body: ConfigBody, _: None = Depends(verify_admin)):
    """更新报名配置（管理员）"""
    set_reg_config(body.key, body.value)
    return {"ok": True}


@app.get("/api/register/list")
def api_reg_list():
    """获取报名列表"""
    return {"registrations": get_registrations(), "count": count_registrations()}


class RegBody(BaseModel):
    name: str
    mmr: int = 0
    race: str = ""
    comment: str = ""

@app.post("/api/register")
def api_register(body: RegBody):
    """选手报名"""
    config = get_reg_config()
    if config.get("open") != "true":
        raise HTTPException(403, "报名通道未开放")
    max_slots = int(config.get("max_slots", "24"))
    if count_registrations() >= max_slots:
        raise HTTPException(403, "报名已满")
    if not body.name.strip():
        raise HTTPException(400, "请填写选手名称")
    reg = add_registration(body.name.strip(), body.mmr, body.race, body.comment)
    return {"ok": True, "registration": reg}


@app.delete("/api/register/{reg_id}")
def api_delete_reg(reg_id: int, _: None = Depends(verify_admin)):
    """删除报名（管理员）"""
    delete_registration(reg_id)
    return {"ok": True}


# ========================================
# 静态页面路由
# ========================================

@app.get("/register")
async def register_page():
    return FileResponse(os.path.join(BISAI_DIR, "register.html"))


# ========================================
# 八强淘汰赛 API
# ========================================
from database import get_conn as db_get_conn
from bracket import (
    get_bracket,
    generate_bracket,
    set_bracket_result,
    reset_bracket,
)

@app.get("/api/bracket")
def api_get_bracket():
    """获取淘汰赛状态"""
    matches = get_bracket()
    conn = db_get_conn()
    players = {}
    for r in conn.execute("SELECT id, name, race FROM players").fetchall():
        players[r["id"]] = {"name": r["name"], "race": r["race"]}
    conn.close()
    
    for m in matches:
        m["player1_name"] = players.get(m.get("player1_id"), {}).get("name", "") if m.get("player1_id") else ""
        m["player2_name"] = players.get(m.get("player2_id"), {}).get("name", "") if m.get("player2_id") else ""
        m["player1_race"] = players.get(m.get("player1_id"), {}).get("race", "") if m.get("player1_id") else ""
        m["player2_race"] = players.get(m.get("player2_id"), {}).get("race", "") if m.get("player2_id") else ""
        winner_name = players.get(m.get("winner_id"), {}).get("name", "") if m.get("winner_id") else ""
        m["winner_name"] = winner_name
    
    return {"matches": matches}


@app.post("/api/bracket/generate")
def api_generate_bracket(_: None = Depends(verify_admin)):
    """根据当前瑞士轮排名生成八强对阵（管理员）"""
    players_raw = get_all_players()
    all_matches = get_all_matches()
    standings = compute_standings(players_raw, all_matches)
    top8 = standings[:8]
    generate_bracket(top8)
    return api_get_bracket()


@app.post("/api/bracket/result/{slot}")
def api_bracket_result(slot: str, winner_id: int, score1: int = 0, score2: int = 0, _: None = Depends(verify_admin)):
    """记录淘汰赛结果（管理员）"""
    ok = set_bracket_result(slot, winner_id, score1, score2)
    if not ok:
        raise HTTPException(400, "操作失败")
    return api_get_bracket()


@app.post("/api/bracket/reset")
def api_reset_bracket(_: None = Depends(verify_admin)):
    """重置淘汰赛（管理员）"""
    reset_bracket()
    return {"ok": True}


@app.get("/bracket")
async def bracket_page():
    return FileResponse(os.path.join(BISAI_DIR, "bracket.html"))


# ========================================
# 设置管理 API
# ========================================

@app.get("/api/settings")
def api_get_settings():
    """获取所有设置（公开）"""
    conn = db_get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


@app.post("/api/settings")
def api_update_settings(body: dict, _: None = Depends(verify_admin)):
    """批量更新设置（管理员）"""
    conn = db_get_conn()
    for key, value in body.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/settings/change-password")
def api_change_password(body: dict):
    """修改管理员密码（需要旧密码验证）"""
    old = body.get("old_password", "")
    new = body.get("new_password", "")
    if not new or len(new) < 4:
        raise HTTPException(400, "新密码至少4位")
    conn = db_get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key='admin_password'").fetchone()
    if not row or row["value"] != old:
        conn.close()
        raise HTTPException(403, "旧密码错误")
    conn.execute("UPDATE settings SET value=? WHERE key='admin_password'", (new,))
    conn.commit()
    conn.close()
    return {"ok": True, "message": "密码已修改"}


@app.get("/admin")
async def admin_page():
    return FileResponse(os.path.join(BISAI_DIR, "admin.html"))

# ========================================
# 仪表盘内容管理 API (零基础可视化编辑)
# ========================================
from dashboard_db import (
    get_all_content as get_dash_content,
    update_content as update_dash_content,
    update_content_batch as update_dash_batch,
    reset_content as reset_dash_content,
    DEFAULT_CONTENT,
)

@app.get("/api/dashboard/content")
def api_get_dashboard_content():
    """获取所有可编辑页面内容"""
    return get_dash_content()

@app.post("/api/dashboard/content")
def api_update_dashboard_content(body: dict, _: None = Depends(verify_admin)):
    """更新页面内容（管理员）"""
    for key, value in body.items():
        update_dash_content(key, str(value))
    return {"ok": True}

@app.post("/api/dashboard/reset")
def api_reset_dashboard_content(_: None = Depends(verify_admin)):
    """重置所有页面内容为默认值"""
    reset_dash_content()
    return {"ok": True}

@app.post("/api/dashboard/upload-banner")
async def api_upload_banner(file: UploadFile = File(...), x_admin_password: str = Header(None)):
    """上传主页Banner图片（管理员）"""
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(401, "管理员密码错误")
    
    IMAGE_DIR = os.path.join(os.path.dirname(__file__), "image")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    ext = os.path.splitext(file.filename or "banner.png")[1] or ".png"
    filename = f"hero-banner{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # 更新配置指向新图片
    update_dash_content("hero_banner_bg", f"image/{filename}")
    
    return {"ok": True, "filename": filename, "url": f"/image/{filename}"}


# ========================================
# 国际化 API
# ========================================
from i18n import load_translations, detect_language

@app.get("/api/lang/{lang}")
def api_get_lang(lang: str = "zh"):
    """获取指定语言的翻译"""
    translations = load_translations(lang)
    return translations

@app.get("/api/lang")
def api_detect_lang(request: Request):
    """检测浏览器语言并返回翻译"""
    lang = detect_language(request)
    translations = load_translations(lang)
    return {"lang": lang, "translations": translations}


# ========================================
# Demo 数据生成 API
# ========================================
@app.post("/api/demo/generate")
def api_generate_demo(_: None = Depends(verify_admin)):
    """生成演示数据：12名假选手 + 2轮比赛结果"""
    from database import get_all_players, get_all_matches, get_conn, TOTAL_ROUNDS, set_current_round
    import random
    
    # 清除现有比赛
    conn = get_conn()
    conn.execute("DELETE FROM matches")
    conn.execute("UPDATE state SET value='0' WHERE key='current_round'")
    
    # 如果已经有选手则跳过，否则生成假选手
    existing = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if existing == 0:
        fake_players = [
            (1, "TyrantZerg", 4800, "z"),
            (2, "BlazeStorm", 4600, "t"),
            (3, "NexusMind", 4500, "p"),
            (4, "ShadowFury", 4400, "z"),
            (5, "IronWill", 4300, "t"),
            (6, "CrystalAura", 4200, "p"),
            (7, "ThunderClap", 4100, "z"),
            (8, "FrostByte", 4000, "t"),
            (9, "EmberWing", 3900, "p"),
            (10, "VoidWalker", 3800, "z"),
            (11, "StarForge", 3700, "t"),
            (12, "MoonLit", 3600, "p"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO players (id, name, mmr, race) VALUES (?, ?, ?, ?)",
            fake_players
        )
        existing = 12
    
    conn.commit()
    conn.close()
    
    # 生成第1轮配对
    from database import get_all_players as gap
    from main import generate_pairings, insert_matches, set_current_round
    players = gap()
    all_matches = []
    round1_pairs = generate_pairings(players, all_matches, 1)
    insert_matches(round1_pairs)
    
    # 随机记录第1轮结果
    conn = get_conn()
    for m in round1_pairs:
        winner = random.choice([m["player1_id"], m["player2_id"]])
        conn.execute("UPDATE matches SET winner_id=? WHERE id=?", (winner, m["id"]))
    
    conn.execute("UPDATE state SET value='1' WHERE key='current_round'")
    conn.commit()
    conn.close()
    
    # 生成第2轮
    all_matches = get_all_matches()
    round2_pairs = generate_pairings(gap(), all_matches, 2)
    insert_matches(round2_pairs)
    
    conn = get_conn()
    for m in round2_pairs:
        winner = random.choice([m["player1_id"], m["player2_id"]])
        conn.execute("UPDATE matches SET winner_id=? WHERE id=?", (winner, m["id"]))
    
    conn.execute("UPDATE state SET value='2' WHERE key='current_round'")
    conn.commit()
    conn.close()
    
    return {
        "ok": True, 
        "message": f"已生成 {existing} 名选手 + 2轮比赛结果",
        "players": existing
    }


@app.post("/api/demo/reset")
def api_reset_demo(_: None = Depends(verify_admin)):
    """清除所有演示数据"""
    from database import get_conn
    conn = get_conn()
    conn.execute("DELETE FROM matches")
    conn.execute("DELETE FROM players")
    conn.execute("UPDATE state SET value='0' WHERE key='current_round'")
    conn.commit()
    conn.close()
    return {"ok": True, "message": "演示数据已清除"}
