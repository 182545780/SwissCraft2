"""Pydantic 数据模型 — 请求/响应结构"""

from pydantic import BaseModel


# ---------- 选手 ----------
class PlayerOut(BaseModel):
    id: int
    name: str
    mmr: int
    race: str = ""


# ---------- 比赛 ----------
class MatchOut(BaseModel):
    id: str
    round: int
    player1_id: int
    player2_id: int
    winner_id: int | None = None


# ---------- 排名条目 ----------
class StandingEntry(BaseModel):
    rank: int
    id: int
    name: str
    mmr: int
    race: str = ""
    wins: int
    opponent_score: int  # 对手分
    games_won: int        # 小局胜场


# ---------- 完整状态 ----------
class StateOut(BaseModel):
    current_round: int
    total_rounds: int
    players: list[PlayerOut]
    pairings: list[MatchOut]
    standings: list[StandingEntry]
    round_complete: bool
    finished: bool  # 全部5轮结束
