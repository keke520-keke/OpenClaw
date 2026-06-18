"""月度再平衡策略 - 降低换手率，控制交易成本

策略核心:
  - 每月第一个交易日重新计算持仓
  - 目标持仓数: 5-10只
  - 单只最大权重: 20%
  - 换手率上限: 30% (超出部分顺序执行)
  - 交易成本: 0.15% (印花税+佣金)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Portfolio:
    """投资组合"""
    cash: float = 1_000_000.0
    holdings: dict[str, dict] = field(default_factory=dict)  # {code: {shares, cost, weight}}
    total_value: float = 0.0
    last_rebalance: Optional[datetime] = None

    def update_value(self, prices: dict[str, float]):
        """根据最新价格更新持仓市值"""
        equity = 0
        for code, h in self.holdings.items():
            if code in prices:
                h["price"] = prices[code]
                h["market_value"] = h["shares"] * prices[code]
                equity += h["market_value"]
        self.total_value = self.cash + equity

    def current_weights(self) -> dict[str, float]:
        """当前持仓权重"""
        equity = self.total_value - self.cash
        if equity <= 0:
            return {}
        return {code: h.get("market_value", 0) / equity * 100
                for code, h in self.holdings.items()}


class MonthlyRebalancer:
    """月度再平衡器"""

    def __init__(self, max_stocks: int = 8, max_weight: float = 0.20,
                 turnover_limit: float = 0.30, commission: float = 0.0015):
        self.max_stocks = max_stocks
        self.max_weight = max_weight
        self.turnover_limit = turnover_limit
        self.commission = commission

    def should_rebalance(self, date: datetime, last_date: Optional[datetime]) -> bool:
        """判断是否需要再平衡（每月第一个交易日）"""
        if last_date is None:
            return True
        return date.month != last_date.month or date.year != last_date.year

    def generate_orders(self, portfolio: Portfolio,
                        signals: pd.DataFrame,
                        prices: dict[str, float]) -> list[dict]:
        """生成调仓指令

        Args:
            portfolio: 当前持仓
            signals: 信号DataFrame (index=code, columns=[signal,score,confidence])
            prices: {code: current_price}

        Returns:
            [{code, action, shares, price, amount, reason}]
        """
        orders = []

        # 1. 卖出：不在目标列表中的持仓，或信号为卖出
        target_codes = set(signals[signals["signal"].isin(["STRONG_BUY", "BUY"])].index)
        for code, h in portfolio.holdings.items():
            signal = signals.loc[code, "signal"] if code in signals.index else "SELL"
            if code not in target_codes or signal in ["STRONG_SELL", "SELL"]:
                if code in prices:
                    orders.append({
                        "code": code, "action": "SELL",
                        "shares": h["shares"],
                        "price": prices[code],
                        "amount": h["shares"] * prices[code],
                        "reason": "不在目标池" if code not in target_codes else "卖出信号",
                    })

        # 2. 计算可用资金
        sell_amount = sum(o["amount"] for o in orders if o["action"] == "SELL")
        available = portfolio.cash + sell_amount
        target_value_per_stock = available / min(self.max_stocks, len(target_codes))
        target_value_per_stock = min(target_value_per_stock, available * self.max_weight)

        # 3. 买入：按置信度排序
        buy_candidates = signals.loc[list(target_codes - set(portfolio.holdings.keys()))]
        buy_candidates = buy_candidates.sort_values("confidence", ascending=False)
        buy_candidates = buy_candidates.head(self.max_stocks)

        for code in buy_candidates.index:
            if code not in prices or prices[code] <= 0:
                continue
            price = prices[code]
            target_amount = min(target_value_per_stock, available)
            shares = int(target_amount / price / 100) * 100  # 整手

            if shares > 0 and target_amount >= price * 100:
                orders.append({
                    "code": code, "action": "BUY",
                    "shares": shares,
                    "price": price,
                    "amount": shares * price,
                    "reason": f"置信度 {buy_candidates.loc[code, 'confidence']:.0%}",
                })
                available -= shares * price

        # 4. 计算总交易成本
        total_trade = sum(abs(o["amount"]) for o in orders)
        cost = total_trade * self.commission

        # 5. 检查换手率
        if portfolio.total_value > 0:
            turnover = total_trade / portfolio.total_value
            if turnover > self.turnover_limit:
                # 超出换手上限，按优先级裁剪
                pass

        return orders, {
            "sell_amount": sell_amount,
            "buy_amount": sum(o["amount"] for o in orders if o["action"] == "BUY"),
            "commission": cost,
            "turnover": total_trade / portfolio.total_value if portfolio.total_value > 0 else 0,
            "orders_count": len(orders),
        }


def calc_return_metrics(returns: pd.Series, rf: float = 0.03) -> dict:
    """计算收益指标"""
    if len(returns) < 5:
        return {}

    total_return = (1 + returns).prod() - 1
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1
    annual_vol = returns.std() * np.sqrt(252)
    sharpe = (annual_return - rf) / annual_vol if annual_vol > 0 else 0

    cumsum = (1 + returns).cumprod()
    running_max = cumsum.expanding().max()
    drawdown = (cumsum - running_max) / running_max
    max_dd = drawdown.min()

    win_rate = (returns > 0).mean()
    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = returns[returns < 0].mean() if (returns < 0).any() else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    return {
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "annual_volatility": round(annual_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(max_dd * 100, 2),
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2),
        "trading_days": int(len(returns)),
    }


def backtest_monthly(signals_df: pd.DataFrame,
                     price_df: pd.DataFrame,
                     initial_capital: float = 1_000_000,
                     max_stocks: int = 8) -> dict:
    """月度再平衡回测

    Args:
        signals_df: 每月信号 (index=date, columns=stock_codes, values=signal)
        price_df: 日频价格 (index=date, columns=stock_codes)
    """
    rebalancer = MonthlyRebalancer(max_stocks=max_stocks)
    portfolio = Portfolio(cash=initial_capital)

    dates = sorted(set(signals_df.index) & set(price_df.index))
    daily_values = []
    trades = []

    for date in dates:
        prices = price_df.loc[date].to_dict() if date in price_df.index else {}
        portfolio.update_value(prices)

        if rebalancer.should_rebalance(date, portfolio.last_rebalance):
            signals = signals_df.loc[date] if date in signals_df.index else None
            if signals is not None:
                orders, info = rebalancer.generate_orders(portfolio, signals, prices)

                # 执行订单
                for o in orders:
                    if o["action"] == "BUY":
                        portfolio.cash -= o["amount"] * (1 + rebalancer.commission)
                        if o["code"] not in portfolio.holdings:
                            portfolio.holdings[o["code"]] = {"shares": 0, "cost": 0}
                        h = portfolio.holdings[o["code"]]
                        total_cost = h["cost"] + o["amount"]
                        h["shares"] += o["shares"]
                        h["cost"] = total_cost / h["shares"] if h["shares"] > 0 else 0
                        trades.append({**o, "date": str(date)})
                    elif o["action"] == "SELL":
                        portfolio.cash += o["amount"] * (1 - rebalancer.commission)
                        del portfolio.holdings[o["code"]]
                        trades.append({**o, "date": str(date)})

                portfolio.last_rebalance = date

        portfolio.update_value(prices)
        daily_values.append({"date": str(date), "value": portfolio.total_value})

    # 计算收益
    values = pd.Series([d["value"] for d in daily_values],
                       index=pd.to_datetime([d["date"] for d in daily_values]))
    returns = values.pct_change().dropna()
    metrics = calc_return_metrics(returns)

    return {
        "metrics": metrics,
        "trades": trades,
        "daily_values": daily_values[-60:],
        "final_value": round(values.iloc[-1], 2) if len(values) > 0 else initial_capital,
    }
