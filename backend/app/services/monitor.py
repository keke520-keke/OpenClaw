"""运维监控 — 系统健康、性能、日志"""

import os
import time
import threading
import traceback
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
from collections import deque

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from loguru import logger


def _cpu_pct():
    return _cpu_pct(interval=0.5) if HAS_PSUTIL else 0.0


def _mem_pct():
    return _mem_pct() if HAS_PSUTIL else 0.0


def _disk_pct():
    return _disk_pct() if HAS_PSUTIL else 0.0


@dataclass
class ComponentStatus:
    """组件状态"""
    name: str
    status: str = "unknown"   # ok / degraded / down
    latency_ms: float = 0
    last_check: str = ""
    error: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class SystemSnapshot:
    """系统快照"""
    timestamp: str
    cpu_pct: float
    memory_pct: float
    disk_pct: float
    api_requests: int = 0
    api_errors: int = 0
    active_users: int = 0
    db_size_mb: float = 0


class SystemMonitor:
    """系统监控器"""

    def __init__(self, history_size: int = 200):
        self.history: deque[SystemSnapshot] = deque(maxlen=history_size)
        self.components: dict[str, ComponentStatus] = {}
        self.api_stats = {"requests": 0, "errors": 0, "latencies": deque(maxlen=100)}
        self.start_time = datetime.now()
        self.last_error_log: deque[dict] = deque(maxlen=50)
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

    def start_monitoring(self, interval: int = 30):
        """启动后台监控"""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        logger.info(f"系统监控已启动 (间隔{interval}s)")

    def stop_monitoring(self):
        self._running = False

    def _monitor_loop(self, interval: int):
        """后台监控循环"""
        while self._running:
            try:
                self._collect()
            except Exception:
                pass
            time.sleep(interval)

    def _collect(self):
        """采集系统指标"""
        snap = SystemSnapshot(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            cpu_pct=_cpu_pct(interval=1),
            memory_pct=_mem_pct(),
            disk_pct=_disk_pct(),
            api_requests=self.api_stats["requests"],
            api_errors=self.api_stats["errors"],
        )
        self.history.append(snap)

    def record_request(self, latency_ms: float, error: bool = False):
        """记录 API 请求"""
        self.api_stats["requests"] += 1
        if error:
            self.api_stats["errors"] += 1
        self.api_stats["latencies"].append(latency_ms)

    def record_error(self, error_msg: str, trace: str = ""):
        """记录错误日志"""
        self.last_error_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": error_msg[:200],
            "trace": trace[:500],
        })

    def check_component(self, name: str, check_fn) -> ComponentStatus:
        """检查组件状态"""
        start = time.time()
        status = ComponentStatus(name=name)
        try:
            result = check_fn()
            latency = (time.time() - start) * 1000
            status.latency_ms = round(latency, 2)
            status.status = "ok" if result else "degraded"
            status.error = "" if result else "检查返回异常"
        except Exception as e:
            status.status = "down"
            status.error = str(e)[:200]
            status.latency_ms = round((time.time() - start) * 1000, 2)
        status.last_check = datetime.now().strftime("%H:%M:%S")
        self.components[name] = status
        return status

    def check_all(self) -> dict:
        """全组件健康检查"""
        # DB
        def check_db():
            from app.database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
                return True
            finally:
                db.close()

        # Redis / Cache (skip for now)
        def check_cache():
            return True  # No Redis configured yet

        # Factor engine
        def check_factors():
            from app.services.factor_engine import FACTOR_REGISTRY
            return len(FACTOR_REGISTRY) > 0

        # Disk space
        def check_disk():
            return _disk_pct() < 90

        checks = [
            ("database", check_db),
            ("cache", check_cache),
            ("factor_engine", check_factors),
            ("disk_space", check_disk),
        ]
        results = {}
        for name, fn in checks:
            self.check_component(name, fn)
            comp = self.components[name]
            results[name] = {
                "status": comp.status,
                "latency_ms": comp.latency_ms,
                "error": comp.error,
            }
        return results

    def get_health_report(self) -> dict:
        """综合健康报告"""
        uptime = datetime.now() - self.start_time
        snap = self.history[-1] if self.history else None

        db_size = 0
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "openclaw.db")
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024 / 1024
        except Exception:
            pass

        latencies = list(self.api_stats["latencies"])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else avg_latency

        return {
            "system": {
                "uptime_hours": round(uptime.total_seconds() / 3600, 1),
                "cpu_pct": snap.cpu_pct if snap else 0,
                "memory_pct": snap.memory_pct if snap else 0,
                "disk_pct": snap.disk_pct if snap else 0,
                "db_size_mb": round(db_size, 2),
                "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "api": {
                "total_requests": self.api_stats["requests"],
                "total_errors": self.api_stats["errors"],
                "error_rate_pct": round(self.api_stats["errors"] / max(self.api_stats["requests"], 1) * 100, 2),
                "avg_latency_ms": round(avg_latency, 1),
                "p95_latency_ms": round(p95_latency, 1),
            },
            "components": {name: {"status": c.status, "latency_ms": c.latency_ms}
                          for name, c in self.components.items()},
            "recent_errors": list(self.last_error_log)[-5:],
            "overall_status": self._overall_status(),
        }

    def _overall_status(self) -> str:
        """综合状态"""
        if not self.components:
            return "unknown"
        statuses = [c.status for c in self.components.values()]
        if "down" in statuses:
            return "degraded"
        if all(s == "ok" for s in statuses):
            return "healthy"
        return "degraded"

    def get_history(self, limit: int = 60) -> list[dict]:
        """获取历史快照"""
        return [{
            "time": s.timestamp,
            "cpu": s.cpu_pct,
            "memory": s.memory_pct,
            "requests": s.api_requests,
        } for s in list(self.history)[-limit:]]


_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
        _monitor.start_monitoring(interval=30)
    return _monitor
