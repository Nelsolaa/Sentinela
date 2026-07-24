# Refatoracao dos services de metricas - 24/07/2026

## Objetivo

Esta refatoracao reorganizou a camada `Services` para separar as regras de negocio de cada
metrica do sistema. Antes da mudanca, CPU, memoria, disco, temperatura, GPU e contexto da
maquina estavam concentrados em `Services/server_metrics_service.py`.

A nova estrutura mantem cada service responsavel por um unico dominio e deixa o service do
servidor apenas como agregador do snapshot completo.

## Estrutura resultante

```text
Services/
|-- system_metrics/
|   |-- __init__.py
|   |-- _converters.py
|   |-- cpu_service.py
|   |-- disco_service.py
|   |-- gpu_service.py
|   |-- memoria_service.py
|   `-- temperatura_service.py
|-- buffer_service.py
|-- machine_context_service.py
|-- metrics_service.py
`-- server_metrics_service.py
```

O nome `system_metrics` diferencia as metricas coletadas da maquina do fluxo generico de
normalizacao e persistencia que ja existe em `Services/metrics_service.py`.

## Responsabilidades

### Services por metrica

Cada arquivo em `Services/system_metrics` importa somente o collector de que precisa e aplica
as regras de apresentacao daquele dominio:

| Service | Responsabilidade |
| --- | --- |
| `cpu_service.py` | padronizar uso, nucleos logicos e frequencia da CPU |
| `memoria_service.py` | nomear valores de memoria em bytes e percentual |
| `disco_service.py` | nomear valores de disco em bytes e percentual |
| `temperatura_service.py` | serializar sensores e tratar indisponibilidade sem derrubar a API |
| `gpu_service.py` | estruturar temperatura, uso e VRAM e identificar `source: mock` |
| `_converters.py` | converter retornos nomeados do `psutil` em dicionarios serializaveis |

Os collectors continuam responsaveis somente pela leitura dos dados brutos. Nenhuma regra de
negocio foi movida para a pasta `Collectors`.

### Contexto da maquina

`Services/machine_context_service.py` passou a concentrar:

- leitura de `SENTINELA_HOST_ID`;
- leitura de `SENTINELA_ENV`;
- normalizacao de `SENTINELA_MACHINE_TYPE`;
- validacao dos valores permitidos `host` e `vm`;
- criacao das tags que identificam a origem das metricas.

Essa regra nao pertence a uma metrica especifica, por isso o arquivo permanece diretamente em
`Services`.

### Agregacao do servidor

`Services/server_metrics_service.py` foi reduzido para a funcao de orquestracao. Ele chama o
contexto da maquina e os cinco services de metricas para montar a resposta consolidada de
`GET /servidor`.

O arquivo deixou de conhecer collectors, detalhes do `psutil`, tratamento de sensores e
formatacao de GPU.

### Controller

`Controllers/server_metrics_controller.py` agora usa diretamente o service correspondente em
cada rota individual. Apenas `GET /servidor` utiliza o agregador.

O fluxo ficou definido assim:

```text
Collector -> Service da metrica -> Controller
                              `-> server_metrics_service -> Controller
```

## Limpeza realizada

O antigo `Services/metricas_service.py` foi removido. Ele continha somente uma segunda
implementacao das metricas de CPU, nao possuia importadores no projeto e duplicava a
responsabilidade assumida por `system_metrics/cpu_service.py`.

`Services/metrics_service.py` foi mantido. Apesar do nome semelhante, esse arquivo normaliza
payloads genericos antes da persistencia e nao substitui os services de metricas do sistema.

## Compatibilidade preservada

A refatoracao nao alterou:

- as rotas `/cpu`, `/memoria`, `/disco`, `/temperatura`, `/gpu` e `/servidor`;
- os nomes dos campos retornados pela API;
- as unidades usadas nos payloads;
- a flag `SENTINELA_MACHINE_TYPE=host|vm`;
- o comportamento controlado quando sensores de temperatura nao estao disponiveis;
- a identificacao da GPU simulada com `source: mock`.

## Testes

Os testes foram reorganizados conforme as novas responsabilidades:

- `tests/test_machine_context_service.py` valida tags e tipos de maquina;
- `tests/test_server_metrics_service.py` valida agregacao e registro das rotas;
- `tests/test_system_metrics_services.py` valida CPU, memoria, disco, temperatura e GPU
  isoladamente, usando retornos controlados dos collectors.

O total passou de 4 para 10 testes automatizados. A execucao usada para validar a entrega foi:

```bash
venv/bin/python -m unittest discover -v
```

Resultado: 10 testes aprovados.

## Beneficios da mudanca

- menor responsabilidade por arquivo;
- regras de cada metrica localizadas em um unico lugar;
- testes unitarios mais diretos;
- menor risco de alterar uma metrica ao trabalhar em outra;
- agregador simples e sem detalhes de coleta;
- estrutura preparada para regras especificas, persistencia e alertas futuros.

## Limites desta entrega

Esta mudanca e estrutural. Ela nao adiciona coleta periodica, persistencia automatica,
dashboard, alerta ou integracao real com GPU AMD. Esses recursos continuam como etapas futuras
do projeto.

## Publicacao

Esta refatoracao foi preparada na branch `agent/unify-system-collectors`, a mesma branch do pull
request [#2](https://github.com/Nelsolaa/Sentinela/pull/2). O commit desta entrega inclui apenas
a reorganizacao dos services, os testes relacionados e este documento.
