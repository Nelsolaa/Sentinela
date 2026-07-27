# Contrato de metricas do Sentinela

## Objetivo

Este documento define os nomes, tipos e unidades persistidos no InfluxDB. Grafana, bot do
Telegram e outros consumidores devem usar este contrato sem inferir unidades pelo valor.

Os collectors continuam retornando dados brutos. Os services convertem e padronizam os
valores, o agente monta um payload plano e a API valida o contrato antes de persistir.

A escrita da API e sincrona: `persisted=true` somente e retornado depois de o InfluxDB aceitar
a metrica. Falhas de escrita acionam o buffer da API.

```text
collectors -> services -> agente -> API -> InfluxDB -> Grafana/Telegram
```

## Measurement

Todas as metricas do snapshot atual usam:

```text
system_metrics
```

## Tags obrigatorias

| Tag | Exemplo | Regra |
| --- | --- | --- |
| `host_id` | `macbook-neo` | identificador estavel da maquina |
| `machine_type` | `host` | aceita somente `host` ou `vm` |
| `environment` | `development` | ambiente de execucao |
| `os` | `darwin` | sistema operacional em minusculas |

As quatro tags devem estar presentes em cada coleta. Isso garante filtros consistentes no
Grafana e consultas confiaveis pelo bot.

## Campos obrigatorios

| Campo | Tipo | Unidade | Origem |
| --- | --- | --- | --- |
| `cpu_usage_percent` | float | percentual de `0` a `100` | CPU real |
| `cpu_logical_cores` | integer | nucleos logicos | CPU real |
| `memory_total_gib` | float | GiB | memoria real |
| `memory_available_gib` | float | GiB | memoria real |
| `memory_used_gib` | float | GiB | memoria real |
| `memory_free_gib` | float | GiB | memoria real |
| `memory_usage_percent` | float | percentual de `0` a `100` | memoria real |
| `disk_total_gib` | float | GiB | disco real |
| `disk_used_gib` | float | GiB | disco real |
| `disk_free_gib` | float | GiB | disco real |
| `disk_usage_percent` | float | percentual de `0` a `100` | disco real |

Esses campos formam o nucleo minimo aceito por `POST /metrics`.

## Campos opcionais

| Campo | Tipo | Unidade | Disponibilidade |
| --- | --- | --- | --- |
| `cpu_frequency_current_mhz` | float | MHz | quando informada pelo sistema |
| `cpu_frequency_min_mhz` | float | MHz | quando informada pelo sistema |
| `cpu_frequency_max_mhz` | float | MHz | quando informada pelo sistema |
| `temperature_available` | boolean | sem unidade | enviada pelo agente |
| `temperature_sensor_count` | integer | sensores | enviada pelo agente |
| `temperature_average_celsius` | float | Celsius | quando existem leituras |
| `temperature_min_celsius` | float | Celsius | quando existem leituras |
| `temperature_max_celsius` | float | Celsius | quando existem leituras |
| `gpu_source` | string | sem unidade | atualmente `mock` |
| `gpu_temperature_celsius` | float | Celsius | atualmente simulada |
| `gpu_usage_percent` | float | percentual de `0` a `100` | atualmente simulada |
| `gpu_vram_used_mib` | integer | MiB | atualmente simulada |
| `gpu_vram_total_mib` | integer | MiB | atualmente simulada |

Temperatura pode estar indisponivel no macOS. Nesse caso, o agente envia
`temperature_available=false` e `temperature_sensor_count=0`, sem os tres campos de leitura.

Dados de GPU devem ser ignorados por alertas reais enquanto `gpu_source=mock`.

## Regras de unidade

- `1 GiB` corresponde a `1024^3` bytes;
- `1 MiB` corresponde a `1024^2` bytes;
- GiB, percentuais, MHz e Celsius sao numeros, nunca textos com unidade;
- os services arredondam valores de ponto flutuante para duas casas quando aplicavel;
- percentuais recebidos do `psutil` ja usam a escala de `0` a `100`;
- o valor `1.0` representa `1%`, e nao `100%`.

Exemplo correto para persistencia:

```json
{
  "memory_used_gib": 10.25,
  "memory_usage_percent": 64.06
}
```

A apresentacao da unidade pertence ao consumidor. O bot pode exibir `10,25 GiB`, mas o
InfluxDB deve continuar armazenando `10.25` como numero.

## Validacao da API

A API rejeita com HTTP `422`:

- ausencia de qualquer campo obrigatorio;
- ausencia de qualquer tag obrigatoria;
- campos ou tags fora das listas deste contrato;
- `machine_type` diferente de `host` ou `vm`;
- texto em campo numerico;
- booleano ou float em campo definido como integer;
- percentual fora da faixa de `0` a `100`;
- capacidade, frequencia ou contagem negativa;
- objetos aninhados, valores infinitos e inteiros fora do limite do InfluxDB.

## Compatibilidade com a fila anterior

O agente converte payloads que ja estavam na fila SQLite antes desta padronizacao:

```text
memory_total_bytes  -> memory_total_gib
disk_free_bytes     -> disk_free_gib
gpu_vram_used_mb    -> gpu_vram_used_mib
```

A compatibilidade existe somente na leitura da fila local. Novas requisicoes HTTP devem usar o
contrato canonico.

## Historico anterior no InfluxDB

Campos antigos, como `memory_total_bytes_gb`, podem continuar presentes no historico do bucket.
Eles nao sao renomeados retroativamente. Novos dashboards e consultas do Telegram devem usar
somente os nomes canonicos deste documento.
