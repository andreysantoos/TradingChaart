# Guia de Contribuição — REA Trading Platform

Agradecemos o interesse em contribuir com a REA Trading Platform.

## Princípios do Projeto
1. Foco em código limpo, testável e sem complexidade desnecessária.
2. Integridade dos dados: granularidade canônica de 1 minuto em UTC, agregação temporal determinística e reconciliação independente.
3. Rotação fluida de ativos sem recriar estado ou recalcular desnecessariamente.

## Como Executar Localmente

### Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest backend/tests
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Script de Validação e Auditoria
```bash
.venv/bin/python backend/scripts/validate_data.py --symbol BTCUSDT --interval 15m --from 2026-11-05T00:00:00 --to 2026-11-05T03:00:00
```

## Regras para Pull Requests
- Toda alteração deve vir acompanhada de testes unitários ou de integração.
- Mantenha a tipagem estrita no TypeScript e verifique o build (`npm run build`).
- Respeite as licenças permissivas e evite introduzir dependências pesadas sem justificativa prévia.
