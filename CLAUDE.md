# OpenClaw - AI 股票量化交易系统 v3.2

## 项目位置
- 根目录: `E:\OpenClaw\`
- 量化工作区: `E:\OpenClaw\Quant_Finance\`
- 文档/计划书: `E:\OpenClaw\docs\`

## 启动方式
```bash
cd E:\OpenClaw\backend
python setup_security.py  # 首次运行，初始化安全配置
python -m uvicorn main:app --host 0.0.0.0 --port 8000

cd E:\OpenClaw\frontend
npx vite --port 5178 --host
```
或双击 `start.bat`

## 技术栈
- 后端: Python FastAPI (uvicorn, port 8000)
- 前端: Vite (port 5178)
- 数据库: SQLite (backend/data/openclaw.db)
- 行情源: 腾讯实时行情 (qt.gtimg.cn)
- 安全: API密钥认证 + CSRF防护 + 速率限制

## 安全配置
```bash
# 初始化安全配置（首次运行）
python setup_security.py

# 验证安全配置
python security_check.py

# 生成API密钥
python -c "from app.security import generate_api_key; print(generate_api_key('my-app', ['read', 'trade']))"
```

## API密钥使用
```bash
# 查询持仓
curl -H "X-API-Key: oc_xxxxx" http://localhost:8000/api/paper/positions

# 执行交易
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: oc_xxxxx" \
  -d '{"code":"600519","side":"buy","quantity":100}' \
  http://localhost:8000/api/paper/order
```

## 关键文件
| 文件 | 说明 |
|------|------|
| `backend/main.py` | 核心引擎：风控/交易/自动扫描/API |
| `backend/app/security.py` | 安全模块：认证/授权/验证/CSRF |
| `backend/app/db_persist.py` | SQLite 持久化层（事务保护） |
| `backend/logs/` | 交易日志（按日期） |
| `backend/data/openclaw.db` | 主数据库 |
| `backend/data/api_keys.json` | API密钥存储 |
| `backend/.env` | 安全配置（密钥/CORS/速率限制） |

## 风控规则
- 总仓位上限: 95%
- 单只仓位上限: 15%（连续亏损降至10%）
- T+1: 当日买入禁止卖出（隔日自动清除）
- 持仓上限: 8只
- 止盈: 20%, 止损: -8%
- 黑天鹅: 上证跌幅 ≥ -5% 全仓强平

## 安全特性
- ✅ API密钥认证（可配置权限）
- ✅ CSRF防护（一次性令牌）
- ✅ 速率限制（100次/分钟，突发20次）
- ✅ 输入验证（股票代码/数量/价格/策略）
- ✅ 日志脱敏（自动隐藏敏感信息）
- ✅ 数据库事务保护（WAL模式）
- ✅ CORS限制（仅允许已知前端域名）
- ✅ 敏感操作POST方法（防CSRF）
- ✅ 文件读取安全检查（路径遍历/扩展名/大小）
- ✅ 全局异常处理（防止信息泄露）

## 关键修复记录
### v3.2 (2026-06-12) - 安全增强版
- 修复命令注入漏洞（urllib替代subprocess）
- 修复CORS完全开放（限制为已知域名）
- 添加API密钥认证系统
- 添加CSRF防护
- 添加速率限制
- 敏感操作改为POST方法
- 添加完整输入验证
- 改进错误处理
- 日志脱敏处理
- 数据库事务保护

### v3.1 (2026-06-10)
- `risk_reset_daily()` 现在会清除 `today_buys`（修复永久T+1死锁）
- `_risk_monitor_loop` 增加了每日日期变更自动触发 `risk_reset_daily()`

