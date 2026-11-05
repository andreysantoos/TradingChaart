#!/usr/bin/env bash
set -e

echo "=== Iniciando REA Trading Platform ==="

# Check virtualenv
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual Python..."
    python3 -m venv .venv
    .venv/bin/pip install -r backend/requirements.txt
fi

# Check frontend node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "Instalando dependencias do frontend..."
    cd frontend && npm install && cd ..
fi

echo "Iniciando backend FastAPI (porta 8000)..."
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Iniciando frontend Vite (porta 5173)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

# Optional background bulk sync
SYNC_PID=""
if [ "$1" = "--sync" ] || [ "$1" = "--ingest" ]; then
    echo "Opção --sync detectada: Iniciando sincronização histórica em segundo plano..."
    .venv/bin/python backend/scripts/download_bulk_history.py --tier intermediate &
    SYNC_PID=$!
fi

trap "echo 'Encerrando serviços...'; kill $BACKEND_PID $FRONTEND_PID $SYNC_PID 2>/dev/null || true" EXIT INT TERM

wait
