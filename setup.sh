#!/usr/bin/env bash
# Setup môi trường PostgreSQL + backend/frontend cho ExamCheat AI (Linux).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== 1. Docker + PostgreSQL =="
if ! command -v docker >/dev/null 2>&1; then
  echo "Chưa có docker, đang cài..."
  sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
  sudo systemctl enable --now docker
fi
if [ ! -f .env ]; then cp .env.example .env; echo "Đã tạo .env từ mẫu"; fi
sudo docker compose up -d postgres
echo "Chờ postgres..."
for i in $(seq 1 20); do
  sudo docker exec examcheat-postgres pg_isready -U examcheat >/dev/null 2>&1 && break
  sleep 2
done
sudo docker exec examcheat-postgres pg_isready -U examcheat

echo "== 2. Backend venv =="
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements.txt

echo "== 3. Frontend =="
.venv/bin/pip install streamlit plotly pandas

echo "Xong. Chạy: .venv/bin/uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000"
echo "Tạo admin: .venv/bin/python backend/scripts/create_admin.py <email> <pass>"
