# Rotas da API Sentinela

Base URL local:

```text
http://127.0.0.1:8000
```

Documentacao interativa da FastAPI:

```text
http://127.0.0.1:8000/docs
```

## Health

| Metodo | Rota | Funcao | Arquivo | Objetivo |
| --- | --- | --- | --- | --- |
| GET | `/health` | `health_check` | `main.py` | Verifica se a API esta online. |

Exemplo de resposta:

```json
{
  "status": "ok"
}
```

## Metricas locais do servidor

Essas rotas coletam dados diretamente da maquina onde a API esta rodando. Elas nao dependem do InfluxDB.

| Metodo | Rota | Funcao da rota | Funcao de service | Objetivo |
| --- | --- | --- | --- | --- |
| GET | `/cpu` | `read_cpu_metrics` | `get_cpu_metrics` | Retorna uso de CPU, quantidade de nucleos logicos e frequencia. |
| GET | `/memoria` | `read_memory_metrics` | `get_memory_metrics` | Retorna total, disponivel, usado, livre e percentual de uso da memoria RAM. |
| GET | `/disco` | `read_disk_metrics` | `get_disk_metrics` | Retorna total, usado, livre e percentual de uso do disco raiz (`/`). |
| GET | `/temperatura` | `read_temperature_metrics` | `get_temperature_metrics` | Retorna sensores de temperatura quando o sistema operacional disponibiliza esses dados. |
| GET | `/gpu` | `read_gpu_metrics` | `get_gpu_metrics` | Retorna metricas simuladas de GPU: temperatura, uso e VRAM. |
| GET | `/servidor` | `read_server_metrics` | `get_server_metrics` | Retorna todas as metricas locais em uma unica resposta. |

Arquivos principais:

```text
Controllers/server_metrics_controller.py
Services/server_metrics_service.py
Collectors/cpu_collector.py
Collectors/memoria_collector.py
Collectors/disco_collector.py
Collectors/temperatura_collector.py
Collectors/gpu_collector.py
```

Exemplo de teste no Insomnia:

```text
GET http://127.0.0.1:8000/cpu
```

Exemplo de resposta de `/cpu`:

```json
{
  "usage_percent": 18.5,
  "logical_cores": 8,
  "frequency_mhz": {
    "current": 2400.0,
    "min": 1200.0,
    "max": 3200.0
  }
}
```

Exemplo de teste para buscar tudo:

```text
GET http://127.0.0.1:8000/servidor
```

A resposta agregada inclui tags que identificam a origem das metricas:

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
  "gpu": {}
}
```

Configure `SENTINELA_MACHINE_TYPE` como `host` ou `vm` no `.env`. A flag identifica a
maquina onde o processo esta executando; ela nao permite que um processo no host colete dados
internos de uma VM.

## Recebimento de metricas

Essa rota recebe uma metrica enviada por outro cliente, agente ou servico. Depois ela normaliza os dados e tenta enviar para o InfluxDB.

| Metodo | Rota | Funcao da rota | Funcoes chamadas | Objetivo |
| --- | --- | --- | --- | --- |
| POST | `/metrics` | `receive_metric` | `prepare_metric`, `send_with_buffer` | Recebe uma metrica, normaliza os campos e tenta persistir no InfluxDB. Se o InfluxDB nao estiver disponivel, guarda em buffer local em memoria. |

Arquivos principais:

```text
Controllers/metrics_controller.py
Services/metrics_service.py
Services/buffer_service.py
infra/influxdb_repository.py
```

Body esperado:

```json
{
  "measurement": "system_metrics",
  "tags": {
    "host": "local"
  },
  "fields": {
    "cpu_percent": 42,
    "memory_bytes": 1073741824
  },
  "timestamp": "2026-07-06T10:00:00Z"
}
```

Campos:

| Campo | Tipo | Obrigatorio | Descricao |
| --- | --- | --- | --- |
| `measurement` | `string` | Nao | Nome da metrica. Padrao: `system_metrics`. |
| `tags` | `object` | Nao | Tags para identificar origem, host, ambiente ou outro agrupamento. |
| `fields` | `object` | Sim | Valores da metrica. Precisa ter pelo menos um campo. |
| `timestamp` | `datetime` | Nao | Data/hora da metrica. Se nao enviado, a API usa o horario atual em UTC. |

Exemplo de teste no Insomnia:

```text
POST http://127.0.0.1:8000/metrics
Content-Type: application/json
```

```json
{
  "measurement": "system_metrics",
  "tags": {
    "host": "local"
  },
  "fields": {
    "cpu_percent": 42,
    "memory_bytes": 1073741824
  }
}
```

Exemplo de resposta quando o InfluxDB nao esta disponivel:

```json
{
  "accepted": true,
  "metric": {
    "measurement": "system_metrics",
    "tags": {
      "host": "local"
    },
    "fields": {
      "cpu_percent": 42.0,
      "memory_bytes_gb": 1.0
    },
    "timestamp": "2026-07-06T13:00:00+00:00"
  },
  "persisted": false,
  "buffered": 1,
  "error": "InfluxDB is not reachable."
}
```

## Como rodar localmente

```bash
cd /Users/nelsonneto/Programacao/Sentinela/Sentinela
source venv/bin/activate
python -m uvicorn main:app --reload
```

Depois teste as rotas no Insomnia, navegador ou na documentacao:

```text
http://127.0.0.1:8000/docs
```
