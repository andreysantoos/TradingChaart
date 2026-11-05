# Correção do gráfico ARPAUSDT — 2026-11-05

Referência inicial: `096f59e`. Comparação solicitada: diário, futuros USDⓈ-M.
Alterações locais; nenhum push ou publicação.

## Causas confirmadas

- O banco tinha 674 candles diários de ARPAUSDT até 05/11/2026. A consulta
  selecionava os primeiros 500, terminando em 15/05/2026. Corrigida para
  selecionar os últimos 500 e devolvê-los em ordem cronológica. Consultas
  com início explícito mantêm paginação para frente.
- O endpoint devolvia o histórico diário importado sem atualizar sua cauda.
  A ingestão incremental de 1m não atualizava esse cache.
- A importação tratava candles abertos como completos e retomava depois
  do último registro, deixando seu fechamento provisório congelado.
- A interface só buscava candles na troca de ativo/timeframe e aceitava
  respostas antigas após uma nova seleção. A legenda arredondava preços
  para duas casas, inadequadas para ARPAUSDT.

## Comportamento implementado

`services/chart_data.py` consulta o timeframe oficial solicitado, persiste
os candles e mantém cache de 60 segundos. Atualizações simultâneas são
serializadas. A interface consulta a cada minuto após a resposta anterior,
mesmo sem troca de ativo. Esse fluxo não exige concluir o histórico de 1m.
A ingestão canônica de 1m continua separada. O motor de agregação e a CLI
existente de reconciliação continuam disponíveis; candles maiores exibidos
pelo gráfico são oficiais, não montados com minutos incompletos.

O candle em formação é identificado na resposta e na interface. O fechamento
considera o instante anterior à consulta: uma resposta que cruza o fechamento
não transforma um snapshot provisório em definitivo. Downloads históricos
excluem candles abertos, e retomadas revisitam o último registro. A ingestão
incremental também revisita a cauda para recuperar snapshots antigos.

Falhas da fonte retornam HTTP 503, e a interface avisa que os dados podem estar
desatualizados. O cache não é renovado em caso de falha. `auto_backfill=false`
permite leitura local sem consulta externa. As respostas da seleção anterior
são descartadas; séries são limpas ao mudar de ativo. Os preços usam a precisão
do instrumento, e atualizações periódicas não forçam o autoscale vertical.

## Verificações executadas

- Backend: `PYTHONPATH=backend .venv/bin/pytest backend/tests -q`:
  **25 aprovados**, um aviso de depreciação do TestClient.
- Interface: `cd frontend && npm test`: **2 aprovados**, cobrindo resposta
  atrasada, atualização periódica, repetição após erro e cancelamento.
- `npm run build`: aprovado, incluindo tipagem TypeScript.
- `npm run lint`: sem erros, três avisos em efeitos React (rotação, legenda
  e dependência inicial de escala).
- `git diff --check`: sem erros.
- Todos os testes de banco agora usam SQLite temporário; não alteram a
  watchlist nem o banco de mercado do usuário.

Conferência real em 05/11/2026: endpoint local
via ASGI e uma segunda consulta pública a `/fapi/v1/klines` da Binance.
Foram atualizados no banco local os últimos 500 candles diários de cada
ativo abaixo, sem excluir seu histórico anterior.

| Ativo | Candles fechados comparados | Divergências OHLCV e volume de cotação |
| --- | ---: | ---: |
| ARPAUSDT | 499 | 0 |
| BTCUSDT | 499 | 0 |
| ETHUSDT | 499 | 0 |

Os três candles atuais foram identificados como provisórios. Seus preços
não foram comparados por igualdade entre consultas, pois mudam durante o dia.

## Limites e aplicação

A amostra valida o caminho de consulta/persistência/resposta nesses ativos;
não equivale à auditoria de todo o banco nem à reconciliação de todas as
agregações de 1m. Snapshots antigos fora da janela consultada não foram
reparados em massa. A atualização depende de conectividade e é polling,
não transmissão em tempo real. Sem gráfico aberto, o serviço de refresh
não consulta todos os timeframes; o coletor incremental continua separado.

Não houve validação visual manual em navegador. Não foram encontrados
processos uvicorn, Vite ou download_bulk_history na inspeção final disponível;
nenhum coletor foi interrompido. Execute `./start.sh` para carregar o código
corrigido. Se existir uma instância em outro ambiente, reinicie-a para aplicar
as alterações; processos Python já iniciados não recebem essas mudanças.
