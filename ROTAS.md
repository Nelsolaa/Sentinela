# Rotas da API Sentinela

Base URL local:

```text
http://127.0.0.1:8000
```

A documentacao interativa fica em `http://127.0.0.1:8000/docs` quando
`SENTINELA_DOCS_ENABLED=true`.

Todas as rotas estao reunidas em `Controllers/monitoring_controller.py`. O controller trata o
protocolo HTTP e chama os services; ele nao coleta, transforma ou persiste dados diretamente.

## Chaves de servico

A API usa duas chaves independentes:

| Header | Uso |
| --- | --- |
| `X-Sentinela-Ingest-Key` | autoriza `POST /metrics` |
| `X-Sentinela-Read-Key` | autoriza as rotas de CPU, memoria, disco, temperatura, GPU e servidor |

As chaves ficam em `SENTINELA_INGEST_API_KEY` e `SENTINELA_READ_API_KEY`. Cada valor deve ter
pelo menos 32 caracteres e pode ser gerado com:

```bash
openssl rand -hex 32
```

Use valores diferentes para leitura e escrita. As chaves devem ser enviadas somente em headers
e nunca em query strings ou URLs.

## Healthcheck

| Metodo | Rota | Autorizacao | Limite padrao |
| --- | --- | --- | --- |
| `GET` | `/health` | publica | 120 requisicoes por minuto e por IP |

Exemplo:

```bash
curl http://127.0.0.1:8000/health
```

Resposta:

```json
{
  "status": "ok"
}
```

## Metricas locais do servidor

Essas rotas consultam a maquina em que a API esta executando. Elas nao leem o historico do
InfluxDB.

| Metodo | Rota | Service | Resultado |
| --- | --- | --- | --- |
| `GET` | `/cpu` | `cpu_service` | uso, nucleos logicos e frequencia |
| `GET` | `/memoria` | `memoria_service` | total, disponivel, usado, livre e percentual |
| `GET` | `/disco` | `disco_service` | total, usado, livre e percentual do disco raiz |
| `GET` | `/temperatura` | `temperatura_service` | sensores disponiveis ou erro generico controlado |
| `GET` | `/gpu` | `gpu_service` | temperatura, uso e VRAM simulados |
| `GET` | `/servidor` | `server_metrics_service` | snapshot completo com tags da maquina |

Todas essas rotas exigem `X-Sentinela-Read-Key` e compartilham o limite padrao de 60
requisicoes por minuto e por IP.

Exemplo:

```bash
curl \
  -H "X-Sentinela-Read-Key: $SENTINELA_READ_API_KEY" \
  http://127.0.0.1:8000/servidor
```

Resposta resumida:

```json
{
  "tags": {
    "host_id": "local-host",
    "machine_type": "host",
    "environment": "development"
  },
  "cpu": {},
  "memoria": {},
  "disco": {},
  "temperatura": {},
  "gpu": {
    "source": "mock"
  }
}
```

Configure `SENTINELA_MACHINE_TYPE` como `host` ou `vm`. A flag identifica o ambiente em que o
processo executa; ela nao permite que um processo no host leia o interior de uma VM.

## Recebimento de metricas

| Metodo | Rota | Autorizacao | Limite padrao |
| --- | --- | --- | --- |
| `POST` | `/metrics` | `X-Sentinela-Ingest-Key` | 30 requisicoes por minuto e por IP |

A rota aceita somente `Content-Type: application/json` e corpos de ate 32 KiB. O measurement
padrao e o unico inicialmente permitido e `system_metrics`.

Exemplo:

```bash
curl \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Sentinela-Ingest-Key: $SENTINELA_INGEST_API_KEY" \
  -d '{
    "measurement": "system_metrics",
    "tags": {
      "host_id": "local-host",
      "environment": "development"
    },
    "fields": {
      "cpu_percent": 42.0,
      "memory_bytes": 1073741824
    }
  }' \
  http://127.0.0.1:8000/metrics
```

### Contrato do payload

| Campo | Regra |
| --- | --- |
| `measurement` | nome permitido, entre 1 e 100 caracteres |
| `tags` | no maximo 20 pares; somente chaves permitidas e valores de ate 256 caracteres |
| `fields` | entre 1 e 50 pares; valores `boolean`, `integer`, `float` finito ou texto curto |
| `timestamp` | data e hora com timezone; se ausente, a API usa UTC atual |

As tags permitidas inicialmente sao `host_id`, `machine_type`, `environment` e `os`. A lista
pode ser ampliada por `SENTINELA_ALLOWED_TAG_KEYS`. Campos desconhecidos, objetos aninhados,
inteiros fora de 64 bits e valores infinitos ou `NaN` sao rejeitados.

Resposta quando a metrica foi colocada no buffer:

```json
{
  "accepted": true,
  "metric": {
    "measurement": "system_metrics",
    "tags": {
      "host_id": "local-host",
      "environment": "development"
    },
    "fields": {
      "cpu_percent": 42.0,
      "memory_bytes_gb": 1.0
    },
    "timestamp": "2026-07-24T13:00:00+00:00"
  },
  "persisted": false,
  "buffered": 1
}
```

A resposta nao inclui mensagens internas do InfluxDB. Quando o buffer atinge sua capacidade,
a API rejeita novas metricas com HTTP 503 em vez de consumir memoria indefinidamente.

## Respostas de seguranca

| Status | Motivo |
| --- | --- |
| `401` | chave ausente ou invalida |
| `413` | corpo maior que o limite permitido |
| `415` | escrita sem `application/json` |
| `422` | payload fora do schema |
| `429` | limite de requisicoes excedido |
| `503` | chaves nao configuradas, buffer cheio ou monitoramento indisponivel |

Respostas limitadas incluem `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining` e
`X-RateLimit-Reset`.

## Execucao local

Instale as dependencias, configure o `.env` e execute um unico worker enquanto o rate limit
usar `memory://`:

```bash
cd /Users/nelsonneto/Programacao/Sentinela/Sentinela
source venv/bin/activate
pip install -r requirements-dev.txt
python -m uvicorn main:app --reload
```

Para producao, desative a documentacao, habilite HTTPS no proxy, configure hosts explicitos e
use um contador compartilhado ou rate limit no reverse proxy caso existam multiplos workers.
