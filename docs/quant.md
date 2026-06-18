---
name: quant
description: 启动量化交易环境——自动扫描E盘02_Quant_Finance目录最新源码（优先读取Codex优化后的磁盘文件），激活虚拟环境，加载数据源和策略引擎
---

# /quant — 量化交易环境启动

## 执行步骤

1. **扫描最新项目**：列出 `E:\ClaudeWorkSpace\02_Quant_Finance\*` 下所有子目录，按修改时间排序
2. **优先Codex代码**：如果存在 `strategies/` 或 `templates/` 下的 `.py` 文件，按修改时间取最新者作为主策略
3. **激活环境**：确认 `quant_venv` 虚拟环境可用，检查已安装包（akshare/pandas-ta-classic/vectorbt/tushare）
4. **加载数据源**：默认使用 AKShare 获取行情，备选 Tushare
5. **显示状态**：报告当前可用策略模板、数据缓存、回测结果概览

## 约束

- 优先读取磁盘最新文件（非会话内旧代码）
- 如虚拟环境损坏，提示手动重建
- 不主动修改策略文件，仅加载和分析
