#!/usr/bin/env bash
# Cài đặt môi trường PostgreSQL + backend/frontend cho ExamCheat AI.
# Hỗ trợ Linux (tự cài Docker) và macOS (dùng Docker Desktop có sẵn).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== 1. Docker + PostgreSQL =="
if ! command -v docker >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Chưa có docker, đang cài..."
    sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
    sudo systemctl enable --now docker
  else
    echo "Chưa có Docker. Hãy cài Docker Desktop rồi chạy lại script này." >&2
    exit 1
  fi
fi

# Linux thường cần sudo, macOS dùng Docker Desktop không cần
if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
elif sudo docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="sudo docker compose"
else
  echo "Không tìm thấy Docker Compose. Cài Docker Desktop hoặc docker-compose-plugin rồi chạy lại." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Đã tạo .env từ mẫu — sửa DATABASE_URL/SECRET_KEY nếu cần"
fi

$DOCKER_COMPOSE up -d postgres
echo "Chờ postgres..."
for _ in $(seq 1 20); do
  $DOCKER_COMPOSE exec -T postgres pg_isready -U examcheat >/dev/null 2>&1 && break
  sleep 2
done
$DOCKER_COMPOSE exec -T postgres pg_isready -U examcheat

echo "== 2. Backend venv =="
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements.txt

echo "== 3. Frontend =="
.venv/bin/pip install -r frontend/requirements.txt

echo "Xong. Chạy: .venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000"
echo "Giao diện: .venv/bin/streamlit run frontend/app.py"
echo "Tài khoản admin mặc định: admin / Admin123 (đổi mật khẩu ngay sau khi đăng nhập)"
