"""纸盘交易 API"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.paper_engine import get_paper_engine

router = APIRouter()
engine = get_paper_engine()
DEFAULT_ACCOUNT = "PAPER_DEFAULT"  # 将在首次请求时替换


def _aid(account_id: str = None) -> str:
    """获取默认账户ID"""
    if account_id:
        return account_id
    # 取第一个账户
    for aid in engine.accounts:
        return aid
    return ""


class OrderRequest(BaseModel):
    code: str
    side: str          # buy / sell
    quantity: int      # 股数（100的倍数）
    price: float = 0.0 # 0=市价
    name: str = ""
    account_id: str = ""


class PriceUpdate(BaseModel):
    prices: dict[str, float]   # {code: price}


@router.get("/account")
async def account_summary(account_id: str = Query("")):
    """账户概览"""
    aid = _aid(account_id)
    data = engine.get_account_summary(aid)
    return {"code": 0, "data": data}


@router.get("/positions")
async def positions(account_id: str = Query("")):
    """持仓列表"""
    aid = _aid(account_id)
    data = engine.get_positions(aid)
    return {"code": 0, "data": data, "count": len(data)}


@router.get("/orders")
async def orders(account_id: str = Query(""), status: str = Query(None)):
    """委托列表"""
    aid = _aid(account_id)
    data = engine.get_orders(aid, status)
    return {"code": 0, "data": data, "count": len(data)}


@router.post("/order")
async def place_order(req: OrderRequest):
    """下单"""
    aid = _aid(req.account_id)
    order = engine.place_order(
        account_id=aid, code=req.code, side=req.side,
        quantity=req.quantity, price=req.price, name=req.name,
    )
    result = {
        "order_id": order.order_id,
        "status": order.status.value,
        "reject_reason": order.reject_reason,
        "filled_price": order.filled_price,
        "filled_qty": order.filled_qty,
        "commission": round(order.commission, 2),
        "pnl": round(order.pnl, 2) if order.pnl else 0,
    }
    return {"code": 0 if order.status.value != "rejected" else 400, "data": result}


@router.post("/cancel/{order_id}")
async def cancel_order(order_id: str, account_id: str = Query("")):
    """撤单"""
    aid = _aid(account_id)
    ok = engine.cancel_order(aid, order_id)
    return {"code": 0 if ok else 404, "msg": "已撤销" if ok else "未找到该委托"}


@router.post("/prices")
async def update_prices(req: PriceUpdate):
    """更新行情（供前端/数据源推送）"""
    engine.update_prices(req.prices)
    return {"code": 0, "msg": f"已更新 {len(req.prices)} 只股票价格"}


@router.get("/stats")
async def trading_stats(account_id: str = Query("")):
    """交易统计"""
    aid = _aid(account_id)
    acc = engine.get_account(aid)
    if not acc:
        return {"code": 404, "msg": "账户不存在"}

    orders = [o for o in acc.order_history if o.status.value == "filled"]
    buy_orders = [o for o in orders if o.side.value == "buy"]
    sell_orders = [o for o in orders if o.side.value == "sell"]

    return {
        "code": 0,
        "data": {
            "total_trades": len(orders),
            "buy_trades": len(buy_orders),
            "sell_trades": len(sell_orders),
            "total_commission": round(sum(o.commission for o in orders), 2),
            "total_realized_pnl": round(acc.total_realized_pnl, 2),
            "win_trades": len([o for o in sell_orders if o.pnl > 0]),
            "loss_trades": len([o for o in sell_orders if o.pnl < 0]),
            "avg_win": round(sum(o.pnl for o in sell_orders if o.pnl > 0) / max(len([o for o in sell_orders if o.pnl > 0]), 1), 2),
            "avg_loss": round(sum(o.pnl for o in sell_orders if o.pnl < 0) / max(len([o for o in sell_orders if o.pnl < 0]), 1), 2),
        },
    }
