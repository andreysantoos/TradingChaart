# REA Trading Platform

Plataforma open source de análise técnica do mercado financeiro, com foco inicial em contratos futuros perpétuos USDⓈ-M e arquitetura voltada para integridade e rotação contínua de ativos.

## Diferenciais Principais

1. **Infraestrutura Canônica de Dados e Reconciliação Independente**:
   - Captura e persistência de candles canônicos de 1 minuto em UTC.
   - Motor de agregação temporal para timeframes maiores (5m, 15m, 30m, 1h, 4h, 1d, 1w) com validação de janelas completas.
   - Mecanismo independente de reconciliação que audita e compara agregações internas diretamente contra os candles oficiais da exchange (estados: `APPROVED`, `DIVERGENT`, `INCOMPLETE`, `PENDING`, `ERROR`).
2. **Rotação Automática de Ativos (Play)**:
   - Permite ao analista configurar indicadores e timeframe uma única vez e alternar automaticamente entre os ativos de uma lista personalizada com temporizador configurável (ex: 5s, 10s, 15s).
   - Preservação estrita do contexto: timeframe, escala linear/logarítmica e configurações de indicadores são mantidos sem recriação desnecessária do gráfico.

3. **Aceleração Quantitativa com Numba JIT**:
   - Compilação nativa em código de máquina LLVM (`@njit(fastmath=True)`) para indicadores iterativos e pesados (Supertrend, ATR, EMA, RSI, Bandas de Bollinger).
4. **Ingestão em Camadas (Top-Down)**:
   - Estratégia dos maiores para os menores timeframes (1w e 1d primeiro, seguidos por 4h, 1h e 15m de 2025 até hoje).
   - Histórico sub-15m (< 15m) restrito ao período recente (a partir do 2º semestre de 2026), otimizando o armazenamento em mais de 95%.

## Atualização e integridade do gráfico

O gráfico consulta candles oficiais de preço negociado da Binance USDⓈ-M
no timeframe selecionado. O backend persiste a janela solicitada e usa cache
de 60 segundos; a interface atualiza a cada minuto, sem depender da conclusão
do download histórico. Os candles maiores exibidos são oficiais, não agregações
parciais de 1m. O motor de agregação e sua reconciliação permanecem disponíveis
separadamente para auditoria da base canônica.

O candle atual é provisório e identificado como “em formação”. Importações
históricas armazenam apenas candles fechados e revisitam o último registro
na retomada. Falhas de atualização são exibidas na interface. O gráfico usa
os 500 candles mais recentes, em ordem cronológica, e preços com a precisão
do instrumento. A atualização é por polling, não por transmissão em tempo real.

Testes da atualização da interface (Node 22.6+): `cd frontend && npm test`.
Detalhes da correção e validação: [DIAGNOSTICO-ARPAUSDT.md](DIAGNOSTICO-ARPAUSDT.md).

## Arquitetura e Tecnologias

- **Frontend**: React 19, TypeScript, Vite, Lightweight Charts (v5), Lucide Icons.
- **Backend / Dados**: Python 3.12, FastAPI, Numba, NumPy, Uvicorn, HTTPX, SQLite em modo WAL.
- **Provedor Inicial**: Binance USDⓈ-M Futures (endpoints públicos REST, sem necessidade de chaves ou credenciais).

## Como Instalar e Executar

### Pré-requisitos
- Node.js >= 20
- Python >= 3.11

### Execução Completa em Um Comando
```bash
./start.sh
```
O script iniciará o backend em `http://127.0.0.1:8000` e o frontend em `http://localhost:5173`.

### Execução Manual por Módulo

#### Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest backend/tests
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run build
npm run dev
```

### Auditoria e Validação Independente dos Dados
Para auditar a consistência de dados agregados de 1m contra candles oficiais da exchange:
```bash
.venv/bin/python backend/scripts/validate_data.py --symbol BTCUSDT --interval 15m --from 2026-11-05T00:00:00 --to 2026-11-05T03:00:00
```

## Licença
Este projeto é distribuído sob os termos da licença [MIT](LICENSE).
