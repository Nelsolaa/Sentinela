# Agente Sentinela

## Funcao

O agente e o processo instalado em cada host ou VM monitorada. A cada ciclo ele:

1. consulta os collectors de CPU, memoria, disco, temperatura e GPU;
2. usa os services para transformar os dados brutos;
3. identifica a maquina, o ambiente e o sistema operacional;
4. grava o payload em uma fila SQLite local;
5. envia as metricas, em ordem, para `POST /metrics`;
6. remove da fila apenas os itens aceitos pela API.

A API continua responsavel por validar, normalizar e persistir o dado no InfluxDB. O Grafana
consulta o InfluxDB e nao se comunica diretamente com o agente.

## Configuracao

Copie `.env.example` para `.env` e configure pelo menos:

```dotenv
SENTINELA_API_URL=http://127.0.0.1:8000
SENTINELA_INGEST_API_KEY=uma-chave-segura-com-pelo-menos-32-caracteres
SENTINELA_HOST_ID=servidor-01
SENTINELA_MACHINE_TYPE=host
SENTINELA_ENV=production
```

Use `SENTINELA_MACHINE_TYPE=vm` quando o processo estiver dentro de uma VM. A flag apenas
identifica a origem; a coleta sempre representa o sistema em que o processo Python executa.

As configuracoes operacionais sao:

| Variavel | Padrao | Funcao |
| --- | --- | --- |
| `SENTINELA_AGENT_INTERVAL_SECONDS` | `60` | intervalo entre ciclos |
| `SENTINELA_AGENT_REQUEST_TIMEOUT_SECONDS` | `10` | timeout de cada chamada HTTP |
| `SENTINELA_AGENT_MAX_ATTEMPTS` | `3` | tentativas por envio |
| `SENTINELA_AGENT_RETRY_BASE_SECONDS` | `1` | base do backoff exponencial |
| `SENTINELA_AGENT_QUEUE_PATH` | `.sentinela/agent_queue.sqlite3` | fila persistente local |
| `SENTINELA_AGENT_QUEUE_MAX_ITEMS` | `10000` | capacidade maxima da fila |
| `SENTINELA_AGENT_FLUSH_BATCH_SIZE` | `20` | envios maximos por ciclo |

O lote padrao de 20 itens permanece abaixo do rate limit padrao de 30 requisicoes por minuto.

## Execucao

Para iniciar InfluxDB, Grafana, API e agente na ordem correta, use o gerenciador local a partir
da raiz do repositorio:

```bash
venv/bin/python manage.py start
venv/bin/python manage.py status
```

O gerenciador deixa API e agente em segundo plano, registra os logs em `.sentinela/logs/` e
impede uma segunda instancia acidental. Para consultar os logs ou encerrar todo o pipeline:

```bash
venv/bin/python manage.py logs --service all
venv/bin/python manage.py stop
```

Os comandos diretos abaixo ficam reservados para diagnostico. Com o ambiente virtual ativado,
execute um unico ciclo para validar somente o agente:

```bash
python agent.py --once
```

O comando retorna `0` quando a metrica foi entregue e `1` quando ela ficou na fila. Para manter
somente o agente coletando continuamente em primeiro plano:

```bash
python agent.py
```

Use `Ctrl+C` para solicitar o encerramento limpo. Em Linux, o mesmo processo pode ser
supervisionado posteriormente pelo `systemd`.

## Falhas e recuperacao

Erros de rede, HTTP 429 e erros temporarios HTTP 5xx usam retry com backoff exponencial. Erros
HTTP permanentes, como chave invalida, nao sao repetidos dentro do mesmo ciclo.

Se a API estiver desligada, o payload permanece na fila SQLite mesmo que o agente reinicie.
Quando a comunicacao voltar, os itens mais antigos sao enviados primeiro. Se a API aceitar o
payload mas o InfluxDB estiver indisponivel, entra em acao o buffer da propria API.

A fila do agente e o buffer da API resolvem falhas diferentes:

```text
agente -- API indisponivel --> fila SQLite do agente
API -- InfluxDB indisponivel --> buffer da API
```

O encerramento do Docker Desktop normalmente desliga InfluxDB e Grafana, mas nao impede a
coleta local do agente. As metricas aguardam enquanto os componentes necessarios estiverem
indisponiveis.

## Payload

Cada ciclo envia um unico measurement `system_metrics` com campos planos para CPU, memoria,
disco, temperatura e GPU. Memoria e disco sao convertidos pelos services para GiB; os valores
continuam numericos para uso pelo Grafana e pelo bot do Telegram. As tags sao `host_id`,
`machine_type`, `environment` e `os`.

O conjunto completo de nomes, tipos e unidades esta em `docs/CONTRATO_METRICAS.md`.

A GPU permanece simulada nesta etapa e o payload inclui `gpu_source=mock`. Esses valores nao
devem ser usados para alertas de producao ate a integracao real com a GPU AMD no Linux.
