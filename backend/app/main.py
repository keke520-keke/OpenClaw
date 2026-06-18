"""OpenClaw - AI股票量化交易系统"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.database import init_db
from app.api import market, screener, factors, ai, backtest, paper, autotrade, auth_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OpenClaw 启动中...")
    init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("OpenClaw 关闭")


app = FastAPI(title="OpenClaw API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/market", tags=["行情"])
app.include_router(screener.router, prefix="/api/screener", tags=["选股器"])
app.include_router(factors.router, prefix="/api/factors", tags=["因子工厂"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI引擎"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测系统"])
app.include_router(paper.router, prefix="/api/paper", tags=["纸盘交易"])
app.include_router(autotrade.router, prefix="/api/autotrade", tags=["自动交易"])
app.include_router(auth_api.router, prefix="/api/auth", tags=["用户认证"])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
