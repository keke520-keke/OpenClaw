"""自动交易 API"""
import random
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.auto_trader import get_auto_trader, AutoTraderState

router = APIRouter()
trader = get_auto_trader()


class RunRequest(BaseModel):
    signals: list[dict] = []   # [{code, name, signal, score, confidence}]
    account_id: str = ""


@router.get("/status")
async def auto_status():
    """自动交易状态"""
    return {
        "code": 0,
        "data": {
            "state": trader.state.value,
            "enabled": trader.config.enabled,
            "trade_count_today": trader.trade_count_today,
            "max_daily_trades": trader.config.max_daily_trades,
            "confidence_threshold": trader.config.signal_confidence_threshold,
            "max_positions": trader.config.max_positions,
            "position_size_pct": trader.config.position_size_pct,
            "stop_loss_pct": trader.config.stop_loss_pct,
            "take_profit_pct": trader.config.take_profit_pct,
            "blacklist": trader.config.blacklist,
        },
    }


@router.post("/toggle")
async def toggle_auto(enabled: bool = Query(True)):
    """开关自动交易"""
    trader.config.enabled = enabled
    return {"code": 0, "msg": f"自动交易已{'开启' if enabled else '关闭'}"}


@router.post("/run")
async def run_auto_cycle(req: RunRequest = None):
    """手动执行一次自动交易循环"""
    from app.services.paper_engine import get_paper_engine

    engine = get_paper_engine()
    aid = list(engine.accounts.keys())[0]

    # 获取行情（从API拉取）
    try:
        import urllib.request, json
        url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=0&np=1&fltt=2&invt=2&fid=f12&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f12,f14"
        req_em = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"})
        with urllib.request.urlopen(req_em, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("data", {}).get("diff", [])
        prices = {str(it["f12"]): float(it.get("f2", 0)) for it in items if it.get("f2")}
    except Exception:
        # 回退到模拟数据
        prices = {f"{600000 + i:06d}": round(random.uniform(8, 200), 2) for i in range(50)}

    # 模拟信号（实际应从AI引擎获取）
    signals = req.signals if req and req.signals else _gen_mock_signals(prices)

    result = trader.run_once(prices, signals, aid)
    return {"code": 0, **result}


@router.get("/logs")
async def auto_logs(limit: int = Query(50)):
    """自动交易日志"""
    return {"code": 0, "data": trader.get_logs(limit)}


@router.get("/alerts")
async def auto_alerts():
    """告警列表"""
    return {"code": 0, "data": trader.get_alerts()}


@router.post("/blacklist/add")
async def add_blacklist(code: str):
    """添加黑名单"""
    if code not in trader.config.blacklist:
        trader.config.blacklist.append(code)
    return {"code": 0, "msg": f"已添加 {code}", "blacklist": trader.config.blacklist}


@router.post("/blacklist/remove")
async def remove_blacklist(code: str):
    """移除黑名单"""
    if code in trader.config.blacklist:
        trader.config.blacklist.remove(code)
    return {"code": 0, "msg": f"已移除 {code}", "blacklist": trader.config.blacklist}


def _gen_mock_signals(prices: dict):
    """生成模拟信号"""
    import random
    random.seed(int(datetime.now().timestamp() / 60))
    signals = []
    names = {"600519": "贵州茅台", "000858": "五粮液", "300750": "宁德时代",
             "002594": "比亚迪", "600036": "招商银行", "601318": "中国平安"}
    for code, price in list(prices.items())[:30]:
        signals.append({
            "code": code, "name": names.get(code, ""),
            "signal": random.choice(["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]),
            "score": round(random.uniform(0, 1), 2),
            "confidence": round(random.uniform(0.3, 0.9), 2),
        })
    return signals
