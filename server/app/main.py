"""
FastAPI Backend for AI Stock Daily Dashboard
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api import routes_dashboard, routes_picks, routes_performance
from app.core.logging_config import setup_logging

# 配置日志
setup_logging(level="INFO", simple=False)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Stock Daily Dashboard API",
    description="每日 AI 选股展示系统",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(routes_dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(routes_picks.router, prefix="/api/v1", tags=["Picks"])
app.include_router(routes_performance.router, prefix="/api/v1", tags=["Performance"])


@app.get("/")
async def root():
    return {"message": "AI Stock Daily Dashboard API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
