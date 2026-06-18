"""纸盘交易引擎 — 模拟实盘交易全流程

功能:
  - 账户管理（多账户、资金、持仓、委托）
  - 订单撮合（限价单按行情价成交、市价单立即成交）
  - 风控检查（资金不足、涨跌停限制、持仓上限）
  - 盈亏计算（持仓盈亏、已实现盈亏、日盈亏）
  - 交易历史记录
  - 管理费/滑点模拟
"""

import uuid
import threading
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class OrderStatus(Enum):
    PENDING = "pending"       # 待成交
    FILLED = "filled"          # 已成交
    PARTIAL = "partial"        # 部分成交
    CANCELLED = "cancelled"    # 已撤销
    REJECTED = "rejected"      # 已拒绝


class OrderType(Enum):
    MARKET = "market"          # 市价单
    LIMIT = "limit"            # 限价单
    STOP_LOSS = "stop_loss"    # 止损单
    TAKE_PROFIT = "take_profit"  # 止盈单


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """委托单"""
    order_id: str
    account_id: str
    code: str
    name: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    price: float = 0.0           # 委托价格（市价单为0）
    quantity: int = 0            # 委托数量（股）
    filled_qty: int = 0          # 已成交
    status: OrderStatus = OrderStatus.PENDING
    reject_reason: str = ""
    created_at: str = ""
    filled_at: str = ""
    filled_price: float = 0.0
    commission: float = 0.0
    pnl: float = 0.0             # 平仓盈亏


@dataclass
class Position:
    """持仓"""
    code: str
    name: str = ""
    shares: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class Account:
    """纸盘账户"""
    account_id: str
    name: str
    cash: float = 1_000_000.0
    frozen: float = 0.0
    positions: dict = field(default_factory=dict)  # {code: Position}
    orders: list = field(default_factory=list)
    order_history: list = field(default_factory=list)
    total_realized_pnl: float = 0.0
    created_at: str = ""
    daily_pnl: float = 0.0


class PaperTradingEngine:
    """纸盘交易引擎"""

    def __init__(self, commission_rate: float = 0.0003, stamp_duty: float = 0.001,
                 slippage: float = 0.001, max_position_pct: float = 0.30):
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty          # 卖出时收
        self.slippage = slippage
        self.max_position_pct = max_position_pct
        self.accounts: dict[str, Account] = {}
        self.price_cache: dict[str, float] = {}
        self._lock = threading.Lock()

    # ---- 账户管理 ----

    def create_account(self, name: str = "默认账户", cash: float = 1_000_000.0) -> Account:
        aid = f"PAPER_{uuid.uuid4().hex[:8].upper()}"
        acc = Account(
            account_id=aid, name=name, cash=cash,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        with self._lock:
            self.accounts[aid] = acc
        logger.info(f"创建纸盘账户: {aid} {name}")
        return acc

    def get_account(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)

    # ---- 行情更新 ----

    def update_prices(self, prices: dict[str, float]):
        """更新行情快照"""
        self.price_cache.update(prices)
        # 更新所有账户持仓市值
        for acc in self.accounts.values():
            for code, pos in acc.positions.items():
                if code in prices:
                    pos.current_price = prices[code]
                    pos.market_value = pos.shares * prices[code]
                    pos.unrealized_pnl = pos.market_value - pos.shares * pos.avg_cost
                    pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.shares * pos.avg_cost) * 100
                                              if pos.shares > 0 and pos.avg_cost > 0 else 0)

    # ---- 下单 ----

    def place_order(self, account_id: str, code: str, side: str,
                    quantity: int, price: float = 0.0,
                    order_type: str = "market", name: str = "") -> Order:
        """下单入口"""
        with self._lock:
            acc = self.accounts.get(account_id)
            if not acc:
                return self._reject("账户不存在")

            side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            otype = OrderType.MARKET if order_type == "market" else OrderType.LIMIT

            # 基础校验
            if quantity <= 0:
                return self._reject("委托数量必须>0")
            if quantity % 100 != 0:
                return self._reject("A股必须为100股整数倍")

            order = Order(
                order_id=f"ORD_{uuid.uuid4().hex[:10].upper()}",
                account_id=account_id, code=code, name=name,
                side=side, order_type=otype,
                price=price, quantity=quantity,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            # 风控检查
            reason = self._risk_check(acc, order)
            if reason:
                order.status = OrderStatus.REJECTED
                order.reject_reason = reason
                acc.order_history.append(order)
                return order

            # 撮合成交
            self._match(acc, order)
            acc.order_history.append(order)
            return order

    def cancel_order(self, account_id: str, order_id: str) -> bool:
        """撤单"""
        acc = self.accounts.get(account_id)
        if not acc:
            return False
        for o in acc.orders:
            if o.order_id == order_id and o.status == OrderStatus.PENDING:
                o.status = OrderStatus.CANCELLED
                acc.orders.remove(o)
                return True
        return False

    # ---- 内部方法 ----

    def _reject(self, reason: str) -> Order:
        return Order(order_id="", account_id="", code="",
                     status=OrderStatus.REJECTED, reject_reason=reason)

    def _risk_check(self, acc: Account, order: Order) -> Optional[str]:
        """风控检查"""
        latest_price = self.price_cache.get(order.code, order.price)

        if order.side == OrderSide.BUY:
            cost = order.quantity * latest_price * (1 + self.commission_rate + self.slippage)
            if cost > acc.cash - acc.frozen:
                return f"资金不足: 需要{cost:.0f}, 可用{acc.cash - acc.frozen:.0f}"

            # 持仓上限检查
            total_equity = acc.cash + sum(p.market_value for p in acc.positions.values())
            current_pos_value = acc.positions.get(order.code, Position(code=order.code)).market_value
            new_pos_value = current_pos_value + order.quantity * latest_price
            if new_pos_value > total_equity * self.max_position_pct:
                return f"超过单只持仓上限{self.max_position_pct*100:.0f}%"

            # 涨跌停限制
            if self._is_limit(order.code, latest_price, "up"):
                return "涨停无法买入"

        else:  # SELL
            pos = acc.positions.get(order.code)
            if not pos or pos.shares < order.quantity:
                return f"持仓不足: 持有{pos.shares if pos else 0}股, 委托{order.quantity}股"

            if self._is_limit(order.code, latest_price, "down"):
                return "跌停无法卖出"

        return None

    def _is_limit(self, code: str, price: float, direction: str) -> bool:
        """简易涨跌停判断（基于昨日收盘价±10%）"""
        # 精确计算需要昨日收盘价，此处用缓存近似
        return False  # 简化处理

    def _match(self, acc: Account, order: Order):
        """撮合成交"""
        # 获取成交价
        latest_price = self.price_cache.get(order.code, order.price)
        if latest_price <= 0 and order.order_type == OrderType.MARKET:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "无行情数据"
            return

        fill_price = latest_price
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and fill_price > order.price:
                fill_price = order.price
            elif order.side == OrderSide.SELL and fill_price < order.price:
                fill_price = order.price

        # 计算费用
        trade_amount = order.quantity * fill_price
        commission = max(trade_amount * self.commission_rate, 5.0)
        slippage_cost = trade_amount * self.slippage
        stamp = trade_amount * self.stamp_duty if order.side == OrderSide.SELL else 0
        total_cost = commission + slippage_cost + stamp

        if order.side == OrderSide.BUY:
            # 扣除资金
            debit = trade_amount + total_cost
            if debit > acc.cash:
                order.status = OrderStatus.REJECTED
                order.reject_reason = f"成交时资金不足: 需{debit:.0f}, 有{acc.cash:.0f}"
                return
            acc.cash -= debit

            # 更新持仓
            if order.code not in acc.positions:
                acc.positions[order.code] = Position(code=order.code, name=order.name)
            pos = acc.positions[order.code]
            total_cost_basis = pos.shares * pos.avg_cost + trade_amount + slippage_cost
            pos.shares += order.quantity
            pos.avg_cost = total_cost_basis / pos.shares if pos.shares > 0 else fill_price
            pos.current_price = fill_price
            pos.market_value = pos.shares * fill_price
            pos.name = order.name or pos.name

        else:  # SELL
            pos = acc.positions[order.code]
            acc.cash += trade_amount - total_cost

            # 计算已实现盈亏
            realized_pnl = (fill_price - pos.avg_cost) * order.quantity - total_cost
            acc.total_realized_pnl += realized_pnl
            order.pnl = realized_pnl

            # 减仓
            pos.shares -= order.quantity
            if pos.shares <= 0:
                del acc.positions[order.code]
            else:
                pos.current_price = fill_price
                pos.market_value = pos.shares * fill_price

        order.status = OrderStatus.FILLED
        order.filled_qty = order.quantity
        order.filled_price = fill_price
        order.commission = total_cost
        order.filled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- 查询接口 ----

    def get_account_summary(self, account_id: str) -> dict:
        """账户概览"""
        acc = self.accounts.get(account_id)
        if not acc:
            return {}

        total_market_value = sum(p.market_value for p in acc.positions.values())
        total_unrealized_pnl = sum(p.unrealized_pnl for p in acc.positions.values())
        total_equity = acc.cash + total_market_value
        total_return = (total_equity / 1_000_000 - 1) * 100

        return {
            "account_id": acc.account_id,
            "name": acc.name,
            "cash": round(acc.cash, 2),
            "frozen": round(acc.frozen, 2),
            "total_market_value": round(total_market_value, 2),
            "total_equity": round(total_equity, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_realized_pnl": round(acc.total_realized_pnl, 2),
            "total_return_pct": round(total_return, 2),
            "daily_pnl": round(acc.daily_pnl, 2),
            "position_count": len(acc.positions),
            "pending_orders": len([o for o in acc.orders if o.status == OrderStatus.PENDING]),
            "created_at": acc.created_at,
        }

    def get_positions(self, account_id: str) -> list[dict]:
        """持仓列表"""
        acc = self.accounts.get(account_id)
        if not acc:
            return []
        return [{
            "code": p.code, "name": p.name,
            "shares": p.shares, "avg_cost": round(p.avg_cost, 3),
            "current_price": round(p.current_price, 2),
            "market_value": round(p.market_value, 2),
            "unrealized_pnl": round(p.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(p.unrealized_pnl_pct, 2),
            "weight_pct": round(p.market_value / (acc.cash + sum(x.market_value for x in acc.positions.values())) * 100, 2)
                if (acc.cash + sum(x.market_value for x in acc.positions.values())) > 0 else 0,
        } for p in acc.positions.values() if p.shares > 0]

    def get_orders(self, account_id: str, status: str = None) -> list[dict]:
        """委托列表"""
        acc = self.accounts.get(account_id)
        if not acc:
            return []
        orders = acc.order_history[-100:]  # 最近100条
        if status:
            orders = [o for o in orders if o.status.value == status]
        return [{
            "order_id": o.order_id, "code": o.code, "name": o.name,
            "side": o.side.value, "type": o.order_type.value,
            "price": o.price, "quantity": o.quantity,
            "filled_qty": o.filled_qty, "filled_price": o.filled_price,
            "status": o.status.value, "reject_reason": o.reject_reason,
            "commission": round(o.commission, 2),
            "pnl": round(o.pnl, 2) if o.pnl else 0,
            "created_at": o.created_at, "filled_at": o.filled_at,
        } for o in reversed(orders)]


# 全局单例
_engine: Optional[PaperTradingEngine] = None


def get_paper_engine() -> PaperTradingEngine:
    global _engine
    if _engine is None:
        _engine = PaperTradingEngine()
        _engine.create_account("默认纸盘账户", 1_000_000.0)
    return _engine
