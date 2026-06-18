---
name: backtest
description: 一键回测——基于vectorbt对当前加载策略执行回测，输出收益曲线、Sharpe比率、最大回撤、胜率
---

# /backtest — 一键回测引擎

## 执行步骤

1. **确认策略**：检查当前是否有已加载策略（来自 /quant）
2. **获取数据**：通过 AKShare 拉取策略所需标的的历史数据（默认近3年日线）
3. **执行回测**：使用 vectorbt 或 trading-strategy-engine 的 BacktestEngine
4. **输出报告**：
   - 累计收益率 (Total Return %)
   - 夏普比率 (Sharpe Ratio)
   - 最大回撤 (Max Drawdown %)
   - 胜率 (Win Rate %)
   - 年化波动率 (Annual Volatility %)
5. **保存结果**：JSON格式存入 `E:\ClaudeWorkSpace\02_Quant_Finance\backtest_results\`

## 快捷参数

- `--period 1y|3y|5y|all` 回测周期
- `--benchmark 000300` 对比基准
- `--plot` 生成可视化图表
