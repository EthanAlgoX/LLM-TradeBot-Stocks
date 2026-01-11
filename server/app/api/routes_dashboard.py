"""
Dashboard API Routes
"""
from fastapi import APIRouter, Query

from app.services import session_loader, performance_service, picks_service

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(preset: str = Query("all", description="股票池预设")):
    """
    首页 Dashboard 数据
    包含：KPI + 今日 Picks + 昨日 Recap + 7 日收益
    """
    # 获取最新 session 信息
    session = session_loader.get_latest_session()
    
    # 7 日收益
    performance = performance_service.get_rolling_performance(days=7, preset=preset)
    
    # 今日选股
    today_picks = picks_service.get_today_picks(preset=preset)
    
    # 昨日复盘
    yesterday_recap = picks_service.get_yesterday_recap(preset=preset)
    
    return {
        "session": session,
        "kpi": performance.get("kpi", {}),
        "performance_7d": performance.get("daily", []),
        "today_picks": today_picks.get("picks", []),
        "yesterday_recap": yesterday_recap.get("trades", []),
        "yesterday_summary": yesterday_recap.get("summary", {})
    }
