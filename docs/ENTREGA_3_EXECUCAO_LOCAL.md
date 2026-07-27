# Entrega 3 - Execucao local automatizada

Data da validacao: 27/07/2026.

## Decisao de arquitetura

A API e o agente executam diretamente no host. Essa organizacao permite que `psutil` leia os
recursos reais do computador monitorado. InfluxDB e Grafana permanecem no Docker para manter
isolamento, persistencia por volumes e inicializacao reproduzivel.

```text
agente no host -> API no host -> InfluxDB no Docker <- Grafana no Docker
```

## Implementacao

O comando `manage.py` passou a controlar o ambiente local:

- `start`: inicia os containers, aguarda os healthchecks, inicia a API e depois o agente;
- `status`: verifica InfluxDB, Grafana, API e agente;
- `logs`: consulta os logs locais da API e do agente;
- `stop`: encerra os processos e os containers sem remover os volumes.

O gerenciador usa lock e arquivos de PID em `.sentinela/runtime/`. Antes de criar um processo,
ele verifica tanto os PIDs gerenciados quanto processos equivalentes iniciados manualmente. Com
isso, uma segunda execucao nao cria outra API nem outro agente.

As imagens foram fixadas em `influxdb:2.9.1` e `grafana/grafana:13.1.1`. Os limites padrao sao:

| Servico | Memoria | CPU |
| --- | --- | --- |
| InfluxDB | 1 GiB | 1 CPU |
| Grafana | 512 MiB | 0,5 CPU |

Esses valores podem ser ajustados pelas variaveis documentadas no `.env.example`.

## Validacao realizada

O teste completo foi executado no macOS com intervalo temporario de 2 segundos, sem alterar o
padrao de 60 segundos do projeto. O resultado foi:

- 54 testes automatizados aprovados;
- configuracao do Compose validada;
- quatro componentes reportados como saudaveis;
- 53 ciclos automaticos persistidos para o host de teste;
- 21 series de campos canonicos com a mesma quantidade de ciclos;
- segundo comando `start` reutilizando os PIDs existentes;
- limites de CPU e memoria confirmados nos containers;
- parada concluida com volumes preservados.

## Proxima entrega

A Entrega 4 consiste em criar os dashboards manualmente no Grafana e exportar os JSONs para o
repositorio. As consultas devem usar o datasource `sentinela-influxdb` e os campos definidos em
`docs/CONTRATO_METRICAS.md`.
