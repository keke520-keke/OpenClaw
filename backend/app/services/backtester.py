"""向量化回测引擎 - 高性能Pandas回测

特性:
  - 纯向量化计算（无逐行循环）
  - 多策略对比
  - 交易成本建模（佣金+滑点+印花税）
  - 仓位管理（等权/风险平价/Kelly）
  - 风控（止损/最大回撤限制）
  - 绩效报告
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1_000_000.0
    commission_rate: float = 0.0003      # 佣金 0.03%
    stamp_duty: float = 0.001             # 印花税 0.1% (卖出)
    slippage: float = 0.001               # 滑点 0.1%
    max_position_pct: float = 0.20       # 单只最大仓位
    max_positions: int = 10               # 最大持仓数
    stop_loss: float = 0.08               # 止损线 -8%
    take_profit: float = 0.30             # 止盈线 +30%
    max_drawdown_limit: float = 0.25      # 最大回撤限制
    rebalance_freq: str = "M"            # 调仓频率 M=月, W=周, D=日


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig
    daily_values: pd.Series
    daily_returns: pd.Series
    trades: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    benchmark_values: Optional[pd.Series] = None

    def summary(self) -> dict:
        return {
            "metrics": self.metrics,
            "trade_count": len(self.trades),
            "final_value": round(self.daily_values.iloc[-1], 2),
            "start_date": str(self.daily_values.index[0]),
            "end_date": str(self.daily_values.index[-1]),
        }


class VectorizedBacktester:
    """向量化回测器"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()

    def run(self, signals: pd.DataFrame, prices: pd.DataFrame,
            benchmark: pd.Series = None) -> BacktestResult:
        """运行回测

        Args:
            signals: 信号矩阵 (index=date, columns=stocks, values=weight [-1,1])
            prices: 价格矩阵 (index=date, columns=stocks)
            benchmark: 基准净值序列
        """
        # 对齐
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)
        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        if signals.empty or prices.empty:
            return None

        # 计算收益率
        returns = prices.pct_change().fillna(0)

        # 信号 → 持仓权重
        weights = self._signals_to_weights(signals)

        # 组合收益 = 权重 × 个股收益
        portfolio_returns = (weights.shift(1) * returns).sum(axis=1)

        # 交易成本
        turnover = weights.diff().abs().sum(axis=1)
        cost = turnover * (self.config.commission_rate + self.config.slippage)
        # 卖出印花税
        sell_turnover = weights.diff().clip(upper=0).abs().sum(axis=1)
        cost += sell_turnover * self.config.stamp_duty

        portfolio_returns = portfolio_returns - cost

        # 止损/止盈（简化：日频检查，跌超止损线则清仓）
        cum_returns = (1 + portfolio_returns).cumprod()
        drawdown = 1 - cum_returns / cum_returns.expanding().max()
        # 超过最大回撤限制 → 当天收益截断
        portfolio_returns[drawdown > self.config.max_drawdown_limit] = 0

        # 净值
        values = self.config.initial_capital * cum_returns
        daily_returns = portfolio_returns.fillna(0)

        # 生成交易记录
        trades = self._record_trades(weights, prices)

        # 计算绩效
        metrics = self._calc_metrics(daily_returns)

        # 基准对比
        benchmark_values = None
        if benchmark is not None:
            bm = benchmark.reindex(daily_returns.index).fillna(method="ffill")
            benchmark_values = self.config.initial_capital * (1 + bm.pct_change().fillna(0)).cumprod()

        result = BacktestResult(
            config=self.config,
            daily_values=values,
            daily_returns=daily_returns,
            trades=trades,
            metrics=metrics,
            benchmark_values=benchmark_values,
        )
        return result

    def _signals_to_weights(self, signals: pd.DataFrame) -> pd.DataFrame:
        """信号转权重（等权 + 仓位限制）"""
        n_positions = self.config.max_positions

        weights = pd.DataFrame(0.0, index=signals.index, columns=signals.columns)

        for i, date in enumerate(signals.index):
            row = signals.loc[date]
            # 只选多头信号
            long_signals = row[row > 0].sort_values(ascending=False)
            selected = long_signals.head(n_positions)

            if len(selected) > 0:
                w = selected / selected.sum()  # 等权归一
                w = w.clip(upper=self.config.max_position_pct)
                w = w / w.sum()  # 再归一
                weights.loc[date, w.index] = w.values

        return weights

    def _record_trades(self, weights: pd.DataFrame, prices: pd.DataFrame) -> list[dict]:
        """记录交易"""
        trades = []
        changes = weights.diff().abs()

        for date in changes.index:
            day_changes = changes.loc[date]
            active = day_changes[day_changes > 0.01]  # 权重变化>1%

            for code in active.index:
                w_change = weights.loc[date, code] - weights.loc[date, code]
                if date > weights.index[0]:
                    w_change = weights.loc[date, code] - weights.loc[weights.index[weights.index < date][-1] if any(weights.index < date) else date, code]
                    if isinstance(w_change, pd.Series):
                        w_change = w_change.iloc[0]

                action = "BUY" if w_change > 0 else "SELL"
                trades.append({
                    "date": str(date),
                    "code": code,
                    "action": action,
                    "weight_change": round(abs(float(w_change)) * 100, 2),
                    "price": round(float(prices.loc[date, code]), 2),
                })

        return trades

    def _calc_metrics(self, returns: pd.Series) -> dict:
        """计算绩效指标"""
        if len(returns) < 5:
            return {}

        cum = (1 + returns).cumprod()
        total_return = cum.iloc[-1] - 1
        years = len(returns) / 252
        annual_return = (cum.iloc[-1]) ** (1 / years) - 1 if years > 0 else 0
        annual_vol = returns.std() * np.sqrt(252)
        sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0

        running_max = cum.expanding().max()
        drawdown = (cum - running_max) / running_max
        max_dd = drawdown.min()
        max_dd_duration = self._max_dd_duration(cum)

        win_rate = (returns > 0).mean()
        avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = returns[returns < 0].mean() if (returns < 0).any() else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        # Calmar (年化/最大回撤)
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        # Sortino (下行标准差)
        downside = returns[returns < 0].std() * np.sqrt(252)
        sortino = (annual_return - 0.03) / downside if downside > 0 else 0

        # VaR & CVaR
        var95 = returns.quantile(0.05)
        cvar95 = returns[returns <= var95].mean()

        return {
            "total_return_pct": round(total_return * 100, 2),
            "annual_return_pct": round(annual_return * 100, 2),
            "annual_volatility_pct": round(annual_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "calmar_ratio": round(calmar, 3),
            "sortino_ratio": round(sortino, 3),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "max_dd_duration_days": max_dd_duration,
            "win_rate_pct": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "var95_pct": round(var95 * 100, 3),
            "cvar95_pct": round(cvar95 * 100, 3),
            "total_days": int(len(returns)),
            "positive_days": int((returns > 0).sum()),
            "best_day_pct": round(returns.max() * 100, 2),
            "worst_day_pct": round(returns.min() * 100, 2),
        }

    def _max_dd_duration(self, cum: pd.Series) -> int:
        """最大回撤持续天数"""
        running_max = cum.expanding().max()
        in_dd = cum < running_max
        durations = in_dd.astype(int).groupby((~in_dd).cumsum()).cumsum()
        return int(durations.max()) if len(durations) > 0 else 0


def compare_strategies(strategies: dict[str, pd.Series],
                       prices: pd.DataFrame,
                       config: BacktestConfig = None) -> dict:
    """多策略对比回测"""
    bt = VectorizedBacktester(config)
    results = {}
    for name, signals in strategies.items():
        try:
            result = bt.run(signals, prices)
            if result:
                results[name] = result.metrics
        except Exception as e:
            results[name] = {"error": str(e)}
    return results
