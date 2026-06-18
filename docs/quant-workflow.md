---
name: quant-workflow
description: Quantitative trading pipeline — AKShare data, pandas-ta indicators, vectorbt backtesting, risk controls
metadata:
  type: project
---

# Quant Workflow
- Data: AKShare 1.18.64 (primary, 800+ APIs) + Tushare 1.4.29 (XBRL supplement)
- Indicators: pandas-ta-classic 0.6.20 (203 indicators, pure Python)
- Backtest: vectorbt 1.0.0 (GPU-accelerated, numba)
- Templates: Backtesting-Framework-QuantTrading + trading-strategy-engine (in E:\ClaudeWorkSpace\02_Quant_Finance\templates\)
- Venv: E:\ClaudeWorkSpace\02_Quant_Finance\quant_venv\

## Risk Control (locked)
- Single position ≤10%, max drawdown -20% stop-loss, leverage ≤2x, sector concentration ≤40%
- /quant: load latest Codex-optimized code from E drive
- /backtest: one-click backtest with Sharpe/MaxDD/WinRate
- /risk: VaR/CVaR/stress test

**Why:** Standardized quant pipeline with locked risk controls.
**How to apply:** Use /quant → /backtest → /risk. See [[project-rules]], [[legacy-resources]].
