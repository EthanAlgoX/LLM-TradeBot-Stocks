"""
Picks API Routes
"""
from fastapi import APIRouter, Query

from app.services import picks_service

router = APIRouter()


@router.get("/picks/today")
async def get_today_picks(preset: str = Query("all", description="股票池预设")):
    """今日选股（BUY 信号）"""
    return picks_service.get_today_picks(preset=preset)


@router.get("/recap/yesterday")
async def get_yesterday_recap(preset: str = Query("all", description="股票池预设")):
    """昨日复盘"""
    return picks_service.get_yesterday_recap(preset=preset)
