# Sentinela

Sentinela e um pipeline local de monitoramento de infraestrutura. Um agente Python coleta
metricas reais do host, envia os dados para uma API FastAPI, persiste as series no InfluxDB e
apresenta CPU, memoria e disco em um dashboard do Grafana.

O projeto esta na fase final do MVP. O fluxo automatico de coleta e visualizacao esta
implementado; servidor Linux, bot do Telegram e GPU AMD real permanecem na proxima fase.

## Funcionalidades

- coleta continua de CPU, memoria e disco com `psutil`;
- identificacao por `host_id`, tipo `host` ou `vm`, ambiente e sistema operacional;
- normalizacao de campos e unidades em services de dominio;
- fila SQLite no agente para indisponibilidade da API;
- buffer na API para indisponibilidade do InfluxDB;
- retry com timeout e backoff exponencial;
- API keys separadas para ingestao e leitura;
- rate limit, limite de payload, hosts confiaveis e headers de seguranca;
- InfluxDB e Grafana executados pelo Docker Compose;
- datasource e dashboard do Grafana provisionados por arquivos versionados;
- comandos unificados para iniciar, diagnosticar e encerrar o pipeline.

Temperatura e opcional no macOS. A GPU continua simulada e identificada como `mock`, portanto
nao deve ser usada em alertas reais.

## Arquitetura

```text
Host monitorado
  collectors -> services -> agente -> fila SQLite
                                  |
                                  v
                              FastAPI
                                  |
                                  v
                              InfluxDB <--- Grafana

Agente e API: host
InfluxDB e Grafana: Docker
```

O agente executa diretamente no host para que os collectors observem a maquina real, e nao os
limites da VM do Docker. InfluxDB e Grafana ficam em containers com volumes persistentes.

## Tecnologias

- Python, FastAPI, Pydantic e Uvicorn;
- `psutil` para metricas do sistema;
- SQLite para a fila persistente do agente;
- InfluxDB 2.9.1;
- Grafana 13.1.1 com consultas Flux;
- Docker Compose;
- `unittest` para testes automatizados.

## Estrutura

```text
Collectors/        coleta de dados brutos
Services/          regras de negocio, agente, fila e buffer
Controllers/       rotas HTTP
Schemas/           validacao dos payloads
Security/          API keys, rate limit e middlewares
infra/             persistencia e gerenciador local
dashboards/        dashboard versionado do Grafana
docker/grafana/    provisioning do datasource e dashboard
tests/             testes automatizados
agent.py           processo de coleta continua
main.py            aplicacao FastAPI
manage.py          operacao do pipeline local
```

## Requisitos

- Python 3.10 ou superior;
- Docker Desktop em execucao;
- Docker Compose disponivel no terminal.

## Configuracao

Na raiz do repositorio:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e substitua todas as credenciais de exemplo. Gere duas chaves diferentes:

```bash
openssl rand -hex 32
```

Use uma chave em `SENTINELA_INGEST_API_KEY` e outra em `SENTINELA_READ_API_KEY`. O dashboard
versionado consulta o bucket `metricas_iniciais`, que ja esta definido no `.env.example`.

Defina a origem monitorada:

```dotenv
SENTINELA_HOST_ID=local-host
SENTINELA_MACHINE_TYPE=host
SENTINELA_ENV=development
```

Use `SENTINELA_MACHINE_TYPE=vm` quando o agente estiver dentro de uma maquina virtual. A coleta
sempre representa o sistema em que o processo Python executa.

## Execucao

Inicie todo o pipeline com um comando:

```bash
venv/bin/python manage.py start
```

O gerenciador inicia InfluxDB e Grafana, aguarda os healthchecks, inicia a API e depois o agente.
Ele tambem impede instancias duplicadas da API e do agente.

```bash
venv/bin/python manage.py status
venv/bin/python manage.py logs --service all --lines 100
venv/bin/python manage.py logs --service agent --lines 50
venv/bin/python manage.py stop
```

O comando `stop` preserva os volumes do Docker e o historico. PIDs, logs e a fila local ficam em
`.sentinela/`, que nao e versionada.

## Acessos Locais

- Grafana: <http://127.0.0.1:3000>
- API e Swagger: <http://127.0.0.1:8000/docs>
- healthcheck da API: <http://127.0.0.1:8000/health>
- InfluxDB: <http://127.0.0.1:8086>

O dashboard `Sentinela - Visao geral` e carregado na pasta `Sentinela` do Grafana e atualiza a
cada minuto. O arquivo V2 do Grafana esta em `dashboards/sentinela-mvp.json` e pode ser usado
para restaurar o dashboard em outra instalacao.

## API

| Metodo | Rota | Funcao | Protecao |
| --- | --- | --- | --- |
| `GET` | `/health` | verifica a API | rate limit |
| `POST` | `/metrics` | recebe uma coleta do agente | chave de ingestao e rate limit |
| `GET` | `/servidor` | retorna o snapshot atual | chave de leitura e rate limit |
| `GET` | `/cpu` | retorna CPU atual | chave de leitura e rate limit |
| `GET` | `/memoria` | retorna memoria atual | chave de leitura e rate limit |
| `GET` | `/disco` | retorna disco atual | chave de leitura e rate limit |

As rotas de leitura exigem o header `X-Sentinela-Read-Key`. A ingestao exige
`X-Sentinela-Ingest-Key`.

## Testes

Execute a suite completa:

```bash
venv/bin/python -m unittest discover -s tests -v
```

Valide tambem o Compose e o estado dos servicos:

```bash
docker compose config --quiet
venv/bin/python manage.py status
```

## Diagnostico

```bash
venv/bin/python manage.py logs --service all
docker compose ps
docker compose logs --tail 100 influxdb grafana
```

Se a API estiver indisponivel, as metricas permanecem na fila SQLite e sao reenviadas em ordem
quando a comunicacao volta. Se o InfluxDB estiver indisponivel, a API tenta preservar as
metricas em seu buffer limitado.

## Documentacao

- [Contrato das metricas](docs/CONTRATO_METRICAS.md)
- [Funcionamento do agente](docs/AGENTE_SENTINELA.md)
- [Execucao local automatizada](docs/ENTREGA_3_EXECUCAO_LOCAL.md)
- [Roadmap do MVP](docs/ROADMAP_MVP.md)

## Escopo Futuro

- bot do Telegram e alertas remotos;
- deploy e supervisao no servidor Linux;
- collector real para GPU AMD;
- temperatura real em plataformas sem suporte do `psutil`;
- HTTPS, VPN ou reverse proxy para acesso remoto;
- backup operacional e GitHub Actions;
- deteccao de anomalias e previsao.

Contribuicoes devem preservar o contrato descrito em `docs/CONTRATO_METRICAS.md` e incluir testes
proporcionais ao comportamento alterado.
