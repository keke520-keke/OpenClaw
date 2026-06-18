"""数据模型 - 表结构定义"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, Index, Text, BigInteger, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class Stock(Base):
    """股票基础信息"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True, comment="股票代码")
    name = Column(String(50), nullable=False, comment="股票名称")
    market = Column(String(10), comment="市场 sh/sz/bj")
    industry = Column(String(50), comment="行业分类")
    listing_date = Column(Date, comment="上市日期")
    is_active = Column(Boolean, default=True, comment="是否退市")
    created_at = Column(DateTime, default=datetime.utcnow)

    # unique=True 自动创建索引，无需显式 Index


class DailyKline(Base):
    """日K线"""
    __tablename__ = "daily_kline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    volume = Column(BigInteger, comment="成交量(股)")
    amount = Column(Float, comment="成交额")
    amplitude = Column(Float, comment="振幅%")
    change_pct = Column(Float, comment="涨跌幅%")
    change_amt = Column(Float, comment="涨跌额")
    turnover_rate = Column(Float, comment="换手率%")
    adj_factor = Column(Float, comment="复权因子")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_kline_code_date", "code", "trade_date"),
        Index("ix_kline_date", "trade_date"),
        {"sqlite_autoincrement": True},
    )


class Factor(Base):
    """因子数据（每只股票每日）"""
    __tablename__ = "factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)

    # 技术因子
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    dif = Column(Float, comment="MACD DIF")
    dea = Column(Float, comment="MACD DEA")
    macd = Column(Float, comment="MACD 柱")
    rsi = Column(Float, comment="RSI(14)")
    k = Column(Float, comment="KDJ K")
    d = Column(Float, comment="KDJ D")
    j = Column(Float, comment="KDJ J")
    boll_upper = Column(Float)
    boll_mid = Column(Float)
    boll_lower = Column(Float)
    vol_ratio = Column(Float, comment="量比")

    # 财务因子
    pe_ratio = Column(Float, comment="市盈率")
    pb_ratio = Column(Float, comment="市净率")
    total_mv = Column(Float, comment="总市值")
    circ_mv = Column(Float, comment="流通市值")

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_factor_code_date", "code", "trade_date"),
        Index("ix_factor_date", "trade_date"),
        {"sqlite_autoincrement": True},
    )


class IndexDaily(Base):
    """指数日线"""
    __tablename__ = "index_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True, comment="指数代码")
    trade_date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    amount = Column(Float)
    change_pct = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_idx_code_date", "code", "trade_date"),)


class SyncLog(Base):
    """数据同步日志"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(50), nullable=False)
    status = Column(String(20), comment="running/success/failed")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    total_records = Column(Integer, default=0)
    error_msg = Column(Text)
