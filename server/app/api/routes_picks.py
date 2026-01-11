"""
Picks API Routes
"""
from typing import Literal
from fastapi import APIRouter, Query

from app.services import picks_service

router = APIRouter()

DataMode = Literal['live', 'backtest']


@router.get("/picks/today")
async def get_today_picks(
    preset: str = Query("all", description="股票池预设"),
    mode: DataMode = Query("backtest", description="数据模式：live/backtest")
):
    """今日选股（BUY 信号）"""
    return picks_service.get_today_picks(preset=preset, mode=mode)


@router.get("/recap/yesterday")
async def get_yesterday_recap(
    preset: str = Query("all", description="股票池预设"),
    mode: DataMode = Query("backtest", description="数据模式：live/backtest")
):
    """昨日复盘"""
    return picks_service.get_yesterday_recap(preset=preset, mode=mode)
