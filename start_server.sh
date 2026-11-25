#!/usr/bin/env bash
# Script khởi động tự động toàn bộ hệ thống ExamCheat AI:
# - PostgreSQL Docker
# - Backend FastAPI (cổng 8000)
# - Frontend Streamlit (cổng 8501)
# - Cloudflare Tunnel (tự động bắt link và cập nhật PUBLIC_EXAM_URL)
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=========================================================="
echo "   ExamCheat AI - Tự động Khởi động Hệ thống (Public & Local)"
echo "=========================================================="

# 1. Khởi động PostgreSQL
echo "[1/4] Kiểm tra PostgreSQL Docker..."
if docker compose version >/dev/null 2>&1; then
    docker compose up -d postgres
elif sudo docker compose version >/dev/null 2>&1; then
    sudo docker compose up -d postgres
fi

# 2. Xử lý dọn dẹp cổng cũ
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8501 | xargs kill -9 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true

PYTHON=".venv/bin/python"
UVICORN=".venv/bin/uvicorn"
STREAMLIT=".venv/bin/streamlit"
if [ ! -d ".venv" ]; then
    PYTHON="python3"
    UVICORN="uvicorn"
    STREAMLIT="streamlit"
fi

# 3. Kiểm tra biến PUBLIC_EXAM_URL trong .env
ENV_PUBLIC_URL=$(grep -E '^PUBLIC_EXAM_URL=' .env 2>/dev/null | cut -d '=' -f2- | tr -d ' "' || true)

# 4. Khởi động Cloudflare Tunnel tự động nếu có cloudflared
CF_BIN=$(which cloudflared 2>/dev/null || echo "/opt/homebrew/bin/cloudflared")
BE_TUNNEL_URL=""
FE_TUNNEL_URL=""

if [ -x "$CF_BIN" ]; then
    echo "[2/4] Khởi tạo Cloudflare Tunnel tự động..."
    
    # Khởi động tunnel Backend
    $CF_BIN tunnel --protocol http2 --url http://localhost:8000 > /tmp/cf_be.log 2>&1 &
    CF_BE_PID=$!
    
    # Khởi động tunnel Frontend
    $CF_BIN tunnel --protocol http2 --url http://localhost:8501 > /tmp/cf_fe.log 2>&1 &
    CF_FE_PID=$!
    
    echo "-> Đang lấy đường link Public từ Cloudflare (khoảng 3 giây)..."
    for i in {1..15}; do
        BE_TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cf_be.log 2>/dev/null | head -n 1 || true)
        FE_TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cf_fe.log 2>/dev/null | head -n 1 || true)
        if [ -n "$BE_TUNNEL_URL" ] && [ -n "$FE_TUNNEL_URL" ]; then
            break
        fi
        sleep 1
    done
fi

# Xác định PUBLIC_EXAM_URL cuối cùng
if [ -n "$ENV_PUBLIC_URL" ]; then
    echo "-> Đang dùng cấu hình cố định trong .env: $ENV_PUBLIC_URL"
    FINAL_EXAM_URL="$ENV_PUBLIC_URL"
elif [ -n "$BE_TUNNEL_URL" ]; then
    echo "-> Đã tự động bắt được link Backend mới: $BE_TUNNEL_URL"
    FINAL_EXAM_URL="$BE_TUNNEL_URL"
    # Tự động cập nhật file .cf_backend_url để Python đọc ngay lập tức
    echo "$BE_TUNNEL_URL" > .cf_backend_url
    # Tự động cập nhật vào .env nếu đang để trống
    sed -i '' "s|^PUBLIC_EXAM_URL=.*|PUBLIC_EXAM_URL=$BE_TUNNEL_URL|" .env 2>/dev/null || true
else
    FINAL_EXAM_URL="http://localhost:8000"
fi

export PUBLIC_EXAM_URL="$FINAL_EXAM_URL"

# 5. Khởi động Backend
echo "[3/4] Khởi động Backend (FastAPI cổng 8000)..."
$UVICORN main:app --app-dir backend --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "-> Backend đã chạy (PID: $BACKEND_PID, Log: backend.log)"
sleep 1

# 6. Hiển thị thông tin và Khởi động Frontend
echo "=========================================================="
echo " 🎉 HỆ THỐNG ĐÃ SẴN SÀNG:"
echo ""
if [ -n "$FE_TUNNEL_URL" ]; then
    echo " 🌐 [PUBLIC] LINK GIÁM THỊ (Frontend):  $FE_TUNNEL_URL"
fi
if [ -n "$BE_TUNNEL_URL" ]; then
    echo " 🌐 [PUBLIC] LINK THÍ SINH (Backend):   $BE_TUNNEL_URL/exam"
fi
echo ""
echo " 💻 [LOCAL]  Link Giám thị máy bạn:       http://localhost:8501"
echo " 💻 [LOCAL]  Link API máy bạn:            http://localhost:8000"
echo "=========================================================="
echo "Nhấn Ctrl+C để dừng toàn bộ hệ thống và tunnel."

# Bắt tín hiệu Ctrl+C để dọn dẹp sạch sẽ
cleanup() {
    echo ""
    echo "Đang dừng hệ thống..."
    kill $BACKEND_PID 2>/dev/null || true
    if [ -n "$CF_BE_PID" ]; then kill $CF_BE_PID 2>/dev/null || true; fi
    if [ -n "$CF_FE_PID" ]; then kill $CF_FE_PID 2>/dev/null || true; fi
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "[4/4] Khởi động giao diện Streamlit..."
$STREAMLIT run frontend/app.py
