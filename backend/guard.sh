#!/bin/bash
# OpenClaw 守护脚本 — 检测进程状态，崩溃自动重启
# 用法：bash guard.sh 或 crontab 每分钟执行

OC_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$OC_DIR/logs/guard.log"
mkdir -p "$OC_DIR/logs"

log() { echo "[$(date '+%H:%M:%S')] $1" >> "$LOG"; }

# 检查后端
check_backend() {
    if ! curl -s --max-time 5 http://localhost:8000/api/health > /dev/null 2>&1; then
        log "BACKEND DOWN — restarting..."
        pkill -f "uvicorn main:app" 2>/dev/null
        sleep 2
        cd "$OC_DIR" && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 >> "$LOG" 2>&1 &
        sleep 5
        if curl -s --max-time 5 http://localhost:8000/api/health > /dev/null 2>&1; then
            log "BACKEND OK"
        else
            log "BACKEND FAIL"
        fi
    fi
}

# 检查前端
check_frontend() {
    if ! curl -s --max-time 5 http://localhost:5178/ > /dev/null 2>&1; then
        log "FRONTEND DOWN — restarting..."
        pkill -f "vite" 2>/dev/null
        sleep 2
        cd "$OC_DIR/../frontend" && nohup npx vite --port 5178 >> "$LOG" 2>&1 &
        sleep 5
        if curl -s --max-time 5 http://localhost:5178/ > /dev/null 2>&1; then
            log "FRONTEND OK"
        else
            log "FRONTEND FAIL"
        fi
    fi
}

log "=== Guard check ==="
check_backend
check_frontend
log "=== Done ==="
