# OpenClaw 交易系统问题修复总结

## 问题诊断

### 1. 止盈止损不生效 ❌ → ✅ 已修复

**问题原因**：
- 止盈止损检查只在`_auto_run_cycle()`中执行
- 该函数只在自动交易开启时运行（`_auto["on"] == True`）
- 如果自动交易未开启，止盈止损永远不会被检查

**修复方案**：
- 创建独立的止盈止损监控线程 `_tp_sl_monitor_loop()`
- 该线程独立运行，不依赖自动交易状态
- 每30秒检查一次持仓的盈亏情况
- 止盈止损触发时自动执行卖出操作
- 新增API端点控制监控启停

### 2. 企业微信推送不工作 ❌ → ✅ 已修复

**问题原因**：
- `_wx()`函数只在买入/卖出成交时调用
- 止盈止损触发时没有调用企业微信推送
- 自动交易启停时没有推送通知

**修复方案**：
- 在止盈止损卖出成功时添加企业微信推送
- 在自动交易启停时添加企业微信推送
- 在T+0模式切换时添加企业微信推送
- 新增`/api/wx/test`端点测试推送功能

### 3. T+0交易不支持 ❌ → ✅ 已修复

**问题原因**：
- T+1检查硬编码在`paper_order()`函数中
- 没有T+0模式开关

**修复方案**：
- 添加`_auto["t0_mode"]`配置项
- T+1检查现在会检查T+0模式开关
- 如果`_auto["t0_mode"] == True`，则允许当日卖出
- 新增API端点配置T+0模式

## 新增功能

### 1. 独立止盈止损监控

```python
# 启动止盈止损监控
POST /api/tp-sl/toggle {"enabled": true}

# 配置止盈止损参数
POST /api/tp-sl/config {"tp": 20.0, "sl": -8.0, "interval": 30}

# 手动触发检查
GET /api/tp-sl/check

# 查看状态
GET /api/tp-sl/status
```

### 2. T+0模式

```python
# 启用T+0模式
POST /api/autotrade/config {"t0_mode": true}

# 禁用T+0模式（恢复T+1）
POST /api/autotrade/config {"t0_mode": false}
```

### 3. 企业微信推送测试

```python
# 测试推送
GET /api/wx/test

# 查看配置
GET /api/wx/config
```

## 修复的代码位置

### 1. 添加T+0模式支持
- **文件**: `main.py:983-985`
- **修改**: T+1检查现在检查`_auto["t0_mode"]`开关

### 2. 独立止盈止损监控
- **文件**: `main.py:1048-1118`
- **新增**: `_tp_sl_check_once()` - 执行一次检查
- **新增**: `_tp_sl_monitor_loop()` - 监控线程
- **新增**: `_start_tp_sl_monitor()` - 启动监控
- **新增**: `_stop_tp_sl_monitor()` - 停止监控

### 3. 企业微信推送增强
- **文件**: `main.py:1070-1075` - 止盈推送
- **文件**: `main.py:1080-1085` - 止损推送
- **文件**: `main.py:1185-1188` - 自动交易启动推送
- **文件**: `main.py:1195-1197` - 自动交易停止推送
- **文件**: `main.py:1230-1232` - T+0模式切换推送

### 4. 新增API端点
- **文件**: `main.py:2832-2895`
  - `GET /api/tp-sl/status` - 监控状态
  - `POST /api/tp-sl/toggle` - 启停监控
  - `POST /api/tp-sl/config` - 配置参数
  - `GET /api/tp-sl/check` - 手动检查
  - `GET /api/wx/test` - 测试推送
  - `GET /api/wx/config` - 推送配置

## 使用指南

### 1. 启用止盈止损监控

```bash
# 启动监控
curl -X POST http://localhost:8000/api/tp-sl/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 查看状态
curl http://localhost:8000/api/tp-sl/status
```

### 2. 配置止盈止损参数

```bash
# 设置止盈20%，止损-8%，每30秒检查
curl -X POST http://localhost:8000/api/tp-sl/config \
  -H "Content-Type: application/json" \
  -d '{"tp": 20.0, "sl": -8.0, "interval": 30}'
```

### 3. 启用T+0模式

```bash
# 启用T+0（允许当日买卖）
curl -X POST http://localhost:8000/api/autotrade/config \
  -H "Content-Type: application/json" \
  -d '{"t0_mode": true}'

# 禁用T+0（恢复T+1）
curl -X POST http://localhost:8000/api/autotrade/config \
  -H "Content-Type: application/json" \
  -d '{"t0_mode": false}'
```

### 4. 测试企业微信推送

```bash
# 测试推送
curl http://localhost:8000/api/wx/test
```

## 自动启动

止盈止损监控会在服务器启动时自动启动，无需手动开启。

如果需要停止监控，可以通过API调用：
```bash
curl -X POST http://localhost:8000/api/tp-sl/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## 注意事项

1. **T+0风险**：T+0模式允许当日买卖，可能增加交易风险，请谨慎使用
2. **止盈止损间隔**：建议设置30-60秒，过短会增加服务器负载
3. **企业微信推送**：确保WX_HOOK配置正确，否则推送会失败
4. **独立监控**：止盈止损监控独立于自动交易，即使自动交易关闭也会运行
