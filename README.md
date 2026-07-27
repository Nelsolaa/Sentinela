# Sentinela

O Sentinela coleta metricas do computador em que o agente Python esta executando, envia os
dados para uma API local, persiste as series no InfluxDB e disponibiliza o datasource para o
Grafana.

## Arquitetura local

```text
macOS: agent.py -> API FastAPI -> Docker: InfluxDB <- Grafana
```

O agente e a API executam diretamente no host. Assim, os collectors leem CPU, memoria e disco
do MacBook em vez dos limites de uma VM do Docker. Somente InfluxDB e Grafana ficam em
containers.

## Preparacao

Requisitos:

- Python 3.10 ou superior;
- Docker Desktop em execucao;
- `docker compose` disponivel no terminal.

Crie o ambiente local:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env`, substitua todas as credenciais de exemplo e gere as chaves da API com:

```bash
openssl rand -hex 32
```

Use valores diferentes em `SENTINELA_INGEST_API_KEY` e `SENTINELA_READ_API_KEY`.

## Operacao

Com o Docker Desktop aberto, inicie todo o pipeline com um comando:

```bash
venv/bin/python manage.py start
```

O gerenciador inicia InfluxDB e Grafana, aguarda os healthchecks, inicia a API e somente entao
inicia o agente. Os processos do host continuam em segundo plano depois que o comando termina.

```bash
venv/bin/python manage.py status
venv/bin/python manage.py logs --service all --lines 100
venv/bin/python manage.py logs --service agent --lines 50
venv/bin/python manage.py stop
```

O comando `stop` encerra agente, API e containers, mas preserva os volumes e o historico. Os
arquivos de PID e logs locais ficam em `.sentinela/`, que nao e versionada. O gerenciador rejeita
uma segunda instancia do agente ou da API para evitar coletas duplicadas.

Depois da inicializacao:

- Grafana: <http://127.0.0.1:3000>
- API e documentacao: <http://127.0.0.1:8000/docs>
- healthcheck da API: <http://127.0.0.1:8000/health>
- InfluxDB: <http://127.0.0.1:8086>

O intervalo padrao do agente e de 60 segundos. Altere
`SENTINELA_AGENT_INTERVAL_SECONDS` somente quando precisar de outro intervalo.

## Diagnostico

Se a inicializacao falhar, consulte primeiro os logs do agente e da API:

```bash
venv/bin/python manage.py logs --service all
docker compose ps
docker compose logs --tail 100 influxdb grafana
```

Se o Docker Desktop estiver fechado, InfluxDB e Grafana nao iniciarao. Quando a API estiver
indisponivel durante a execucao direta do agente, as metricas permanecem na fila SQLite em
`.sentinela/agent_queue.sqlite3` e sao reenviadas em ordem quando a comunicacao volta.

## Documentacao

- [Contrato das metricas](docs/CONTRATO_METRICAS.md)
- [Funcionamento do agente](docs/AGENTE_SENTINELA.md)
- [Execucao local automatizada](docs/ENTREGA_3_EXECUCAO_LOCAL.md)
- [Roadmap do MVP](docs/ROADMAP_MVP.md)

Os dashboards sao criados manualmente no Grafana e seus JSONs devem ser exportados para o
repositorio durante a Entrega 4 do roadmap.
