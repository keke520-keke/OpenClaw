"""全自动交易闭环 — AI信号→筛选→风控→下单→监控

自动交易流程:
  1. 获取最新行情 → 更新纸盘引擎价格
  2. 计算因子 → AI生成信号
  3. 信号过滤（置信度>阈值、排除涨停/跌停）
  4. 与当前持仓对比 → 生成调仓指令
  5. 风控检查 → 执行下单
  6. 记录日志 → 发送告警
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger


class AutoTraderState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class AutoTraderConfig:
    """自动交易配置"""
    enabled: bool = False
    signal_confidence_threshold: float = 0.60   # 最低置信度
    max_positions: int = 8                       # 最大持仓
    position_size_pct: float = 0.15              # 单只仓位比例
    min_cash_reserve: float = 50000              # 最低现金保留
    rebalance_interval_minutes: int = 60         # 调仓间隔
    max_daily_trades: int = 20                   # 每日最大交易次数
    stop_loss_pct: float = -8.0                  # 止损线
    take_profit_pct: float = 20.0                # 止盈线
    blacklist: list = field(default_factory=list) # 黑名单


@dataclass
class TradeSignal:
    """交易信号"""
    code: str
    name: str
    action: str  # BUY / SELL / HOLD
    score: float
    confidence: float
    price: float
    reason: str = ""


@dataclass
class AutoTradeLog:
    """自动交易日志"""
    timestamp: str
    event: str
    code: str = ""
    details: str = ""
    level: str = "INFO"  # INFO / WARN / ALERT


class AutoTrader:
    """自动交易引擎"""

    def __init__(self):
        self.config = AutoTraderConfig()
        self.state = AutoTraderState.IDLE
        self.logs: list[AutoTradeLog] = []
        self.alerts: list[dict] = []
        self.trade_count_today: int = 0
        self.trade_date: str = ""
        self._thread: Optional[threading.Thread] = None
        self._paper_engine = None
        self._signal_generator = None
        self._on_alert: Optional[Callable] = None

    def configure(self, **kwargs):
        """更新配置"""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self._log("CONFIG", f"配置更新: {kwargs}")

    # ---- 核心交易逻辑 ----

    def run_once(self, prices: dict[str, float], signals: list[dict] = None,
                 account_id: str = "") -> dict:
        """执行一次自动交易循环

        Args:
            prices: {code: price} 最新行情
            signals: AI生成的信号 [{code, name, signal, score, confidence}]
            account_id: 目标账户

        Returns:
            {orders_placed, alerts_triggered, summary}
        """
        from app.services.paper_engine import get_paper_engine

        if not self.config.enabled:
            return {"status": "disabled", "orders": []}

        self._paper_engine = get_paper_engine()
        if account_id and account_id not in self._paper_engine.accounts:
            return {"status": "error", "msg": "账户不存在"}

        aid = account_id or list(self._paper_engine.accounts.keys())[0]
        acc = self._paper_engine.get_account(aid)

        # 0. 每日重置交易计数
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.trade_date:
            self.trade_count_today = 0
            self.trade_date = today

        # 1. 更新行情
        self._paper_engine.update_prices(prices)
        self._log("PRICES", f"更新 {len(prices)} 只股票行情")

        # 2. 生成调仓指令
        orders_placed = []

        if signals:
            trade_signals = self._signals_to_actions(signals, prices, acc)
            self._log("SIGNALS", f"信号处理: {len(trade_signals)} 个交易信号")

            # 3. 执行止损/止盈检查
            stop_orders = self._check_stop_orders(acc, prices)
            trade_signals.extend(stop_orders)

            # 4. 按优先级执行
            for ts in sorted(trade_signals, key=lambda x: -abs(x.confidence))[:self.config.max_daily_trades - self.trade_count_today]:
                if self.trade_count_today >= self.config.max_daily_trades:
                    self._log("LIMIT", "达到每日交易上限", level="WARN")
                    break

                qty = self._calc_position_size(acc, ts.price, self.config.position_size_pct)
                if qty < 100:
                    continue

                order = self._paper_engine.place_order(
                    account_id=aid, code=ts.code, side=ts.action.lower(),
                    quantity=qty, price=ts.price, name=ts.name,
                )

                if order.status.value == "filled":
                    self.trade_count_today += 1
                    orders_placed.append({
                        "code": ts.code, "name": ts.name,
                        "action": ts.action, "qty": qty,
                        "price": order.filled_price,
                        "reason": ts.reason,
                    })
                    self._log("TRADE", f"{ts.action} {ts.name}({ts.code}) x{qty} @{order.filled_price:.2f} — {ts.reason}")
                elif order.status.value == "rejected":
                    self._log("REJECT", f"{ts.code} {order.reject_reason}", level="WARN")

        # 5. 检查告警
        alerts = self._check_alerts(acc, prices)

        account_summary = self._paper_engine.get_account_summary(aid)

        return {
            "status": "completed",
            "account_id": aid,
            "orders_placed": orders_placed,
            "alerts": alerts,
            "trade_count_today": self.trade_count_today,
            "max_trades": self.config.max_daily_trades,
            "account": account_summary,
        }

    # ---- 信号处理 ----

    def _signals_to_actions(self, signals: list[dict], prices: dict,
                            acc) -> list[TradeSignal]:
        """AI信号 → 交易动作"""
        actions = []
        current_codes = set(acc.positions.keys())

        for sig in signals:
            code = sig.get("code", "")
            if code in self.config.blacklist:
                continue
            if sig.get("confidence", 0) < self.config.signal_confidence_threshold:
                continue
            if code not in prices:
                continue

            signal_type = sig.get("signal", "HOLD")
            price = prices[code]
            name = sig.get("name", "")

            if signal_type in ("STRONG_BUY", "BUY"):
                if code not in current_codes:
                    # 开新仓
                    pos_count = len(current_codes) + len([a for a in actions if a.action == "BUY"])
                    if pos_count < self.config.max_positions:
                        actions.append(TradeSignal(
                            code=code, name=name, action="BUY",
                            score=sig.get("score", 0),
                            confidence=sig.get("confidence", 0),
                            price=price, reason=f"AI买入信号 置信度{sig.get('confidence',0):.0%}",
                        ))
                else:
                    # 已有持仓且信号增强 → 加仓
                    pos = acc.positions.get(code)
                    if pos and pos.market_value < (acc.cash + sum(p.market_value for p in acc.positions.values())) * self.config.position_size_pct:
                        actions.append(TradeSignal(
                            code=code, name=name, action="BUY",
                            score=sig.get("score", 0),
                            confidence=sig.get("confidence", 0) * 0.5,
                            price=price, reason="加仓信号",
                        ))

            elif signal_type in ("STRONG_SELL", "SELL"):
                if code in current_codes:
                    actions.append(TradeSignal(
                        code=code, name=name, action="SELL",
                        score=sig.get("score", 0),
                        confidence=sig.get("confidence", 0),
                        price=price, reason=f"AI卖出信号",
                    ))

        return actions

    def _check_stop_orders(self, acc, prices: dict) -> list[TradeSignal]:
        """止损/止盈检查"""
        actions = []
        for code, pos in acc.positions.items():
            if code not in prices:
                continue
            current_price = prices[code]
            pnl_pct = (current_price - pos.avg_cost) / pos.avg_cost * 100

            if pnl_pct <= self.config.stop_loss_pct:
                actions.append(TradeSignal(
                    code=code, name=pos.name, action="SELL",
                    score=1.0, confidence=1.0, price=current_price,
                    reason=f"止损 ({pnl_pct:.1f}%)",
                ))
            elif pnl_pct >= self.config.take_profit_pct:
                actions.append(TradeSignal(
                    code=code, name=pos.name, action="SELL",
                    score=1.0, confidence=1.0, price=current_price,
                    reason=f"止盈 ({pnl_pct:.1f}%)",
                ))
        return actions

    def _calc_position_size(self, acc, price: float, pct: float) -> int:
        """计算仓位大小（取整到100股）"""
        equity = acc.cash + sum(p.market_value for p in acc.positions.values())
        target = equity * pct
        available = max(acc.cash - self.config.min_cash_reserve, 0)
        amount = min(target, available)
        shares = int(amount / price / 100) * 100
        return max(shares, 0)

    def _check_alerts(self, acc, prices: dict) -> list[dict]:
        """生成告警"""
        alerts = []
        summary = acc.cash + sum(p.market_value for p in acc.positions.values())

        # 总资产大幅下跌 (>5%)
        if summary < 950_000:
            pct = (summary / 1_000_000 - 1) * 100
            alerts.append({
                "type": "DRAWDOWN", "level": "ALERT",
                "msg": f"总资产回撤 {pct:.1f}%",
                "value": round(summary, 0),
            })

        # 单只持仓亏损 > 止损线
        for code, pos in acc.positions.items():
            if code in prices:
                pnl = (prices[code] - pos.avg_cost) / pos.avg_cost * 100
                if pnl < self.config.stop_loss_pct:
                    alerts.append({
                        "type": "STOP_LOSS", "level": "WARN",
                        "code": code, "msg": f"触发止损线 ({pnl:.1f}%)",
                        "pnl_pct": round(pnl, 2),
                    })

        return alerts

    # ---- 日志 ----

    def _log(self, event: str, msg: str, level: str = "INFO"):
        log = AutoTradeLog(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            event=event, details=msg, level=level,
        )
        self.logs.append(log)
        if len(self.logs) > 500:
            self.logs = self.logs[-200:]
        if level in ("WARN", "ALERT"):
            self.alerts.append({"time": log.timestamp, "event": event, "msg": msg, "level": level})
            self.alerts = self.alerts[-50:]

    def get_logs(self, limit: int = 50) -> list[dict]:
        return [{"time": l.timestamp, "event": l.event, "msg": l.details, "level": l.level}
                for l in self.logs[-limit:]]

    def get_alerts(self) -> list[dict]:
        return self.alerts[-20:]


# 全局单例
_auto_trader: Optional[AutoTrader] = None


def get_auto_trader() -> AutoTrader:
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AutoTrader()
    return _auto_trader
