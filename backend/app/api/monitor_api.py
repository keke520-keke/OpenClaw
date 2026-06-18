"""运维监控 API"""
from fastapi import APIRouter, Query
from app.services.monitor import get_monitor

router = APIRouter()
monitor = get_monitor()


@router.get("/health")
async def health_report():
    """综合健康报告"""
    report = monitor.get_health_report()
    return {"code": 0, **report}


@router.get("/components")
async def component_status():
    """组件状态"""
    components = monitor.check_all()
    return {"code": 0, "components": components, "overall": monitor._overall_status()}


@router.get("/history")
async def performance_history(limit: int = Query(60)):
    """性能历史"""
    data = monitor.get_history(limit)
    return {"code": 0, "data": data, "count": len(data)}


@router.get("/stats")
async def runtime_stats():
    """运行时统计"""
    report = monitor.get_health_report()
    return {
        "code": 0,
        "uptime_hours": report["system"]["uptime_hours"],
        "total_requests": report["api"]["total_requests"],
        "error_rate_pct": report["api"]["error_rate_pct"],
        "avg_latency_ms": report["api"]["avg_latency_ms"],
        "p95_latency_ms": report["api"]["p95_latency_ms"],
        "overall": report["overall_status"],
    }


@router.post("/check")
async def manual_check():
    """手动触发全量检查"""
    components = monitor.check_all()
    report = monitor.get_health_report()
    return {"code": 0, "components": components, "overall": report["overall_status"]}
