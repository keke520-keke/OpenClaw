"""SQLite 持久化层 — 纸盘交易数据不丢失（安全增强版）"""
import os
import json
import sqlite3
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "openclaw.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ═══════════════════════════════════════════
# 安全的数据库连接管理
# ═══════════════════════════════════════════
@contextmanager
def _get_connection():
    """安全的数据库连接上下文管理器"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
        conn.execute("PRAGMA busy_timeout=5000")  # 忙时等待5秒
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise Exception(f"数据库错误: {e}")
    finally:
        if conn:
            conn.close()


def init():
    """初始化数据库表"""
    with _get_connection() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS paper_accounts (
                account_id TEXT PRIMARY KEY,
                cash REAL DEFAULT 1000000,
                realized_pnl REAL DEFAULT 0,
                total_commission REAL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                shares INTEGER,
                avg_cost REAL,
                buy_date TEXT,
                UNIQUE(code)
            );
            CREATE TABLE IF NOT EXISTS paper_orders (
                order_id TEXT PRIMARY KEY,
                time TEXT,
                code TEXT,
                name TEXT,
                side TEXT,
                qty REAL,
                price REAL,
                fee REAL,
                pnl REAL DEFAULT 0,
                status TEXT,
                strategy TEXT DEFAULT 'manual',
                stamp REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                tax REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS paper_today_buys (
                code TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS watchlists (
                group_name TEXT,
                code TEXT,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY(group_name, code)
            );
            CREATE TABLE IF NOT EXISTS risk_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                msg TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS risk_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_orders_time ON paper_orders(time);
            CREATE INDEX IF NOT EXISTS idx_orders_code ON paper_orders(code);
        """)


# ===== 账户 =====
def save_account(account_id: str, cash: float, realized_pnl: float, total_commission: float):
    """保存账户信息"""
    with _get_connection() as c:
        now = datetime.now().isoformat()
        c.execute("""
            INSERT OR REPLACE INTO paper_accounts (account_id, cash, realized_pnl, total_commission, created_at, updated_at)
            VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM paper_accounts WHERE account_id=?), ?), ?)
        """, (account_id, cash, realized_pnl, total_commission, account_id, now, now))


def load_account(account_id: str):
    """加载账户信息"""
    with _get_connection() as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM paper_accounts WHERE account_id=?", (account_id,)).fetchone()
        if row:
            return {"cash": row["cash"], "realized_pnl": row["realized_pnl"], "total_commission": row["total_commission"]}
        return None


# ===== 持仓 =====
def save_positions(positions: dict):
    """保存当前持仓（使用事务）"""
    with _get_connection() as c:
        c.execute("BEGIN TRANSACTION")
        try:
            c.execute("DELETE FROM paper_positions")
            for code, pos in positions.items():
                c.execute("INSERT INTO paper_positions (code, name, shares, avg_cost, buy_date) VALUES (?,?,?,?,?)",
                          (code, pos.get("name", ""), pos.get("shares", 0), pos.get("avg_cost", 0), pos.get("buy_date", "")))
            c.execute("COMMIT")
        except Exception as e:
            c.execute("ROLLBACK")
            raise Exception(f"保存持仓失败: {e}")


def load_positions() -> dict:
    """加载持仓"""
    with _get_connection() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM paper_positions").fetchall()
        positions = {}
        for r in rows:
            positions[r["code"]] = {
                "name": r["name"], "shares": r["shares"],
                "avg_cost": r["avg_cost"], "buy_date": r["buy_date"],
            }
        return positions


# ===== 订单 =====
def save_order(order: dict):
    """保存订单"""
    with _get_connection() as c:
        c.execute("""
            INSERT OR REPLACE INTO paper_orders (order_id, time, code, name, side, qty, price, fee, pnl, status, strategy, stamp, commission, tax)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (order.get("id"), order.get("time"), order.get("code"), order.get("name"),
              order.get("side"), order.get("qty"), order.get("price"), order.get("fee"),
              order.get("pnl", 0), order.get("status"), order.get("strategy", "manual"),
              order.get("stamp", 0), order.get("commission", 0), order.get("tax", 0)))


def load_orders() -> list:
    """加载订单"""
    with _get_connection() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM paper_orders ORDER BY time").fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["order_id"], "time": r["time"], "code": r["code"], "name": r["name"],
                "side": r["side"], "qty": r["qty"], "price": r["price"], "fee": r["fee"],
                "pnl": r["pnl"], "status": r["status"], "strategy": r["strategy"],
                "stamp": r["stamp"], "commission": r["commission"], "tax": r["tax"],
            })
        return result


# ===== 今日买入 =====
def save_today_buys(codes: set):
    """保存今日买入记录"""
    with _get_connection() as c:
        c.execute("DELETE FROM paper_today_buys")
        for code in codes:
            c.execute("INSERT INTO paper_today_buys (code) VALUES (?)", (code,))


def load_today_buys() -> set:
    """加载今日买入记录"""
    with _get_connection() as c:
        rows = c.execute("SELECT code FROM paper_today_buys").fetchall()
        return {r[0] for r in rows}


# ===== 自选股 =====
def save_watchlist(groups: dict):
    """保存自选股"""
    with _get_connection() as c:
        c.execute("DELETE FROM watchlists")
        for group, codes in groups.items():
            for i, code in enumerate(codes):
                c.execute("INSERT INTO watchlists (group_name, code, sort_order) VALUES (?,?,?)",
                          (group, code, i))


def load_watchlist() -> dict:
    """加载自选股"""
    with _get_connection() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM watchlists ORDER BY group_name, sort_order").fetchall()
        groups = {}
        for r in rows:
            groups.setdefault(r["group_name"], []).append(r["code"])
        return groups


# ===== 风控配置 =====
def save_risk_config(key: str, value):
    """保存风控配置"""
    with _get_connection() as c:
        c.execute("INSERT OR REPLACE INTO risk_config (key, value) VALUES (?,?)",
                  (key, json.dumps(value)))


def load_risk_config() -> dict:
    """加载风控配置"""
    with _get_connection() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM risk_config").fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}


# ===== 统计 =====
def get_stats():
    """获取统计信息"""
    with _get_connection() as c:
        orders = c.execute("SELECT COUNT(*) FROM paper_orders").fetchone()[0]
        positions = c.execute("SELECT COUNT(*) FROM paper_positions").fetchone()[0]
        return {"orders": orders, "positions": positions}
