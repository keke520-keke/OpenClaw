# 🤖 AI 量化交易系统 OpenClaw v3.2

> 解压后先看这份指南，按步骤操作，10分钟内就能跑起来。

---

## 你需要装什么（两个免费软件）

| 软件 | 下载地址 | 安装注意 |
|------|---------|---------|
| **Python 3.8+** | https://www.python.org/downloads/ | ⚠️ 安装时一定勾选底部 "Add Python to PATH" |
| **Node.js LTS** | https://nodejs.org/ | 一路下一步即可 |

**装完后验证**：打开 cmd（Win+R → 输入cmd → 回车），分别输入：
```
python --version    → 应该显示 Python 3.x.x
node --version      → 应该显示 v18.x.x 或更高
```

---

## 怎么跑起来（5步）

### 第1步：安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```
> 如果报错，试试 `pip3 install -r requirements.txt` 或 `py -m pip install -r requirements.txt`

### 第2步：初始化安全配置
```bash
python setup_security.py
python security_check.py
```
> 看到 "✅ 安全配置通过" 就对了

### 第3步：启动后端（保持这个窗口开着）
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
> 看到 `Uvicorn running on http://0.0.0.0:8000` → 后端启动成功 ✅

### 第4步：启动前端（再开一个cmd窗口）
```bash
cd frontend
npm install
npx vite --port 5178 --host
```
> 看到 `Local: http://localhost:5178/` → 前端启动成功 ✅

### 第5步：打开浏览器
地址栏输入：**http://localhost:5178**

---

## 你会看到什么

- 📊 **行情面板**：实时股票数据（腾讯行情源）
- 📈 **K线图表**：日K/周K/月K
- 🧠 **因子分析**：多因子选股评分
- 🔄 **回测系统**：历史数据回测 + 收益曲线
- 🛡️ **风控面板**：持仓管理、止盈止损、仓位监控

---

## 常见报错解决

| 报错信息 | 原因 | 解决 |
|----------|------|------|
| `'python' 不是内部或外部命令` | Python没装或没加PATH | 重装Python，**勾选 Add to PATH** |
| `ModuleNotFoundError: No module named 'xxx'` | 依赖没装全 | 重新执行 `pip install -r requirements.txt` |
| `Address already in use` | 8000端口被占用 | 换端口：`--port 8001` |
| 前端页面空白 | 后端没启动 | 确认第3步的cmd窗口还在运行 |
| `npm: command not found` | Node.js没装 | 去 nodejs.org 下载安装 |

---

## 文件结构

```
OpenClaw/
├── README.md          ← 你正在看的
├── start.bat          ← Windows双击一键启动
├── backend/           ← Python后端
│   ├── main.py        ← 主程序入口
│   ├── requirements.txt
│   └── app/           ← 核心代码
├── frontend/          ← Vue前端
└── docs/              ← 文档
```

---

## 重要提示

⚠️ 本系统默认运行在**模拟交易模式**，所有交易均为虚拟操作，不涉及真实资金。
⚠️ 实盘交易需自行配置券商API密钥。**投资有风险，入市需谨慎。**
⚠️ 本源码仅供学习研究使用。

---

## 还是搞不定？

- 截图报错信息，闲鱼私聊我
