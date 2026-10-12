#!/bin/bash
# 个人 PM macOS 管理脚本
# 用法: ./pm.sh [start|stop|restart|status]
#   start   启动（默认）：后端 @ 8765（直接托管前端，日常使用只需这个）
#   stop    停止全部服务
#   restart 重启
#   status  查看运行状态

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/backend/.venv/bin/python"
BACKEND_PORT=8765
FRONTEND_PORT=5173
BACKEND_LOG=/tmp/personal-pm-backend.log
FRONTEND_LOG=/tmp/personal-pm-frontend.log

port_in_use() {
    lsof -i :"$1" -sTCP:LISTEN >/dev/null 2>&1
}

stop_all() {
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        if port_in_use "$port"; then
            echo "→ 停止端口 $port 上的进程 ..."
            kill $(lsof -t -i :"$port" -sTCP:LISTEN) 2>/dev/null
            sleep 1
        else
            echo "→ 端口 $port 未占用，跳过"
        fi
    done
    echo "✓ 已停止（后端 + 前端）"
}

start_backend() {
    if port_in_use $BACKEND_PORT; then
        echo "⚠ 后端已在运行 : http://localhost:$BACKEND_PORT"
        return
    fi
    echo "→ 启动后端 (FastAPI @ $BACKEND_PORT) ..."
    cd "$ROOT/backend" || exit 1
    nohup "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    for i in $(seq 1 15); do
        port_in_use $BACKEND_PORT && break
        sleep 1
    done
    if port_in_use $BACKEND_PORT; then
        echo "✓ 后端就绪 : http://localhost:$BACKEND_PORT"
        echo "  日志: $BACKEND_LOG"
    else
        echo "✗ 后端启动超时，请查看日志: $BACKEND_LOG"
        exit 1
    fi
}

start_frontend() {
    if port_in_use $FRONTEND_PORT; then
        echo "⚠ 前端已在运行 : http://localhost:$FRONTEND_PORT"
        return
    fi
    echo "→ 启动前端开发模式 (Vite @ $FRONTEND_PORT) ..."
    cd "$ROOT/frontend" || exit 1
    nohup npm run dev -- --host 127.0.0.1 --port $FRONTEND_PORT > "$FRONTEND_LOG" 2>&1 &
    for i in $(seq 1 30); do
        port_in_use $FRONTEND_PORT && break
        sleep 1
    done
    if port_in_use $FRONTEND_PORT; then
        echo "✓ 前端就绪 : http://localhost:$FRONTEND_PORT"
        echo "  日志: $FRONTEND_LOG"
    else
        echo "✗ 前端启动超时，请查看日志: $FRONTEND_LOG"
    fi
}

show_status() {
    echo "🚀 个人 PM 状态"
    echo "────────────────────────────────"
    if port_in_use $BACKEND_PORT; then
        echo "● 后端 FastAPI : http://localhost:$BACKEND_PORT  运行中"
    else
        echo "○ 后端 FastAPI : http://localhost:$BACKEND_PORT  未运行"
    fi
    if port_in_use $FRONTEND_PORT; then
        echo "● 前端 Vite    : http://localhost:$FRONTEND_PORT  运行中（开发模式）"
    else
        echo "○ 前端 Vite    : http://localhost:$FRONTEND_PORT  未运行"
    fi
    echo "────────────────────────────────"
}

case "${1:-start}" in
    start)
        start_backend
        echo "📌 访问地址: http://localhost:$BACKEND_PORT（日常使用，后端直接托管前端）"
        ;;
    dev)
        start_backend
        start_frontend
        echo "📌 开发模式: 前端 http://localhost:$FRONTEND_PORT"
        ;;
    stop)
        stop_all
        ;;
    restart)
        echo "↻ 重启服务 ..."
        stop_all
        sleep 1
        start_backend
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: ./pm.sh [start|dev|stop|restart|status]"
        echo "  start   启动后端（默认，日常使用）"
        echo "  dev     启动后端 + 前端开发模式"
        echo "  stop    停止全部"
        echo "  restart 重启后端"
        echo "  status  查看状态"
        exit 1
        ;;
esac
