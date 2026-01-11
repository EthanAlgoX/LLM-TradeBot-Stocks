"""
Performance API Routes
"""
from typing import Literal
from fastapi import APIRouter, Query

from app.services import performance_service

router = APIRouter()

DataMode = Literal['live', 'backtest']


@router.get("/performance/rolling")
async def get_rolling_performance(
    days: int = Query(7, ge=1, le=60, description="滚动天数"),
    preset: str = Query("all", description="股票池预设"),
    mode: DataMode = Query("backtest", description="数据模式：live/backtest")
):
    """获取滚动 N 日收益"""
    return performance_service.get_rolling_performance(days=days, preset=preset, mode=mode)

