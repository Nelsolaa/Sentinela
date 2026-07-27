# Roadmap do MVP Sentinela

## 1. Definicao de pronto

O MVP do Sentinela estara pronto quando, no ambiente local de desenvolvimento:

1. o agente coletar CPU, memoria e disco continuamente no host;
2. as metricas forem enviadas sem chamadas manuais;
3. os dados forem persistidos no InfluxDB;
4. o Grafana consultar o InfluxDB por um datasource provisionado;
5. os dashboards forem criados automaticamente ao iniciar a stack;
6. CPU, memoria, disco e ultima coleta puderem ser acompanhados pelo navegador;
7. o procedimento completo puder ser repetido a partir do repositorio.

O servidor Linux, o bot do Telegram e recursos preditivos nao fazem parte deste MVP.

## 2. Estado atual

| Componente | Estado | Observacao |
| --- | --- | --- |
| collectors | concluido | CPU, memoria e disco usam dados reais do host |
| services de metricas | concluido | transformam os dados brutos e montam o snapshot |
| identificacao da maquina | concluido | envia `host_id`, `machine_type`, `environment` e `os` |
| agente continuo | concluido no codigo | executa ciclos periodicos depois de iniciado |
| fila local do agente | concluido | SQLite preserva metricas quando a API esta indisponivel |
| autenticacao e retry | concluido | chave de ingestao, timeout e backoff implementados |
| API de ingestao | concluido | `POST /metrics` validado, protegido e limitado |
| escrita no InfluxDB | validada | teste real persistiu 21 campos em 24/07/2026 |
| InfluxDB e Grafana | concluido em branch separada | stack Docker esta no PR Docker |
| datasource do Grafana | concluido em branch separada | provisioning aponta para InfluxDB com Flux |
| execucao local automatizada | pendente | API e agente ainda precisam ser iniciados separadamente |
| dashboards provisionados | pendente | nenhum dashboard JSON esta versionado |
| validacao reproduzivel | pendente | falta testar a solucao consolidada a partir da `main` |

## 3. Caminho critico

### Entrega 1 - Consolidar as branches

Objetivo: colocar infraestrutura e aplicacao na mesma base antes de criar dashboards.

- revisar e mesclar o PR da stack Docker;
- revisar e mesclar o PR do agente, services, controller e seguranca;
- resolver o conflito esperado em `.env.example`;
- alinhar `INFLUXDB_ORG` e `INFLUXDB_BUCKET` entre Compose, API e documentacao;
- preservar as chaves do agente e as credenciais da stack no exemplo de ambiente;
- executar todos os testes depois da integracao;
- validar `docker compose config` na versao consolidada.

**Criterio de aceite:** a branch `main` contem agente, API, Compose, InfluxDB, datasource do
Grafana e testes, sem depender de arquivos existentes apenas em outra branch.

### Entrega 2 - Congelar o contrato das metricas

Objetivo: garantir que os dashboards usem nomes de campos estaveis.

- listar os campos realmente persistidos no measurement `system_metrics`;
- corrigir nomes ambiguos como `memory_total_bytes_gb`, caso ainda sejam produzidos;
- definir unidades finais para bytes, GiB, MHz, Celsius e percentuais;
- manter CPU, memoria e disco como dados reais obrigatorios;
- tratar temperatura como opcional no macOS;
- manter a GPU identificada como `mock` e fora dos indicadores principais;
- registrar o contrato final em documentacao e testes.

**Criterio de aceite:** uma coleta possui campos planos, unidades documentadas e nomes que nao
precisarao ser alterados durante a criacao dos dashboards.

### Entrega 3 - Automatizar a execucao local

Objetivo: iniciar a coleta completa sem abrir e configurar dois terminais manualmente.

- manter o agente diretamente no macOS para que `psutil` observe o host real;
- manter InfluxDB e Grafana no Docker;
- decidir se a API sera executada no host ou em container separado;
- criar comandos documentados de `start`, `status`, `logs` e `stop`;
- iniciar a API antes do agente e aguardar o healthcheck;
- executar o agente com intervalo padrao de 60 segundos;
- impedir duas instancias acidentais do agente para o mesmo `host_id`;
- fixar as imagens em `influxdb:2.9.1` e `grafana/grafana:13.1.1`;
- configurar limites de recursos adequados ao MacBook.

**Criterio de aceite:** um unico comando inicia o pipeline e novas metricas aparecem no
InfluxDB a cada ciclo, sem executar `agent.py --once` manualmente.

### Entrega 4 - Criar os dashboards do Grafana

Objetivo: transformar as series do InfluxDB na experiencia minima de monitoramento.

- adicionar provisioning de dashboards ao Compose;
- versionar os dashboards como JSON no repositorio;
- usar o datasource com UID `sentinela-influxdb`;
- adicionar filtros por `host_id` e `environment`;
- criar painel de uso atual e historico de CPU;
- criar painel de memoria usada e percentual;
- criar painel de disco usado, livre e percentual;
- criar painel de ultima coleta por host;
- indicar visualmente quando um host parou de enviar dados;
- ocultar temperatura quando o sensor nao estiver disponivel;
- identificar qualquer painel de GPU como dado simulado.

**Criterio de aceite:** um Grafana novo carrega os dashboards automaticamente e apresenta os
dados reais do MacBook sem configuracao manual pela interface.

### Entrega 5 - Validacao final do MVP

Objetivo: comprovar que o fluxo completo e repetivel e se recupera de falhas simples.

- iniciar a solucao usando somente o repositorio e um `.env` valido;
- confirmar os healthchecks da API, InfluxDB e Grafana;
- manter o agente ativo por pelo menos cinco ciclos;
- comparar uma coleta da maquina com os valores exibidos no dashboard;
- desligar a API durante uma coleta e confirmar o crescimento da fila SQLite;
- religar a API e confirmar que a fila retorna a zero;
- reiniciar Grafana e InfluxDB sem perder os dashboards nem o historico;
- revisar logs para garantir que chaves e tokens nao sejam expostos;
- documentar instalacao, execucao, parada e diagnostico no README.

**Criterio de aceite:** todos os testes acima passam e outra pessoa consegue subir o ambiente
seguindo apenas a documentacao do repositorio.

## 4. Ordem de execucao

| Ordem | Entrega | Dependencia |
| --- | --- | --- |
| 1 | consolidar branches | nenhuma |
| 2 | congelar contrato das metricas | consolidacao |
| 3 | automatizar execucao local | contrato definido |
| 4 | criar dashboards | dados e campos estaveis |
| 5 | validar o MVP completo | todas as entregas anteriores |

Os dashboards nao devem ser criados antes da consolidacao e da definicao final dos campos.
Caso contrario, qualquer mudanca de nome ou unidade obrigara a refazer as consultas do Grafana.

## 5. Checklist de conclusao

- [ ] PR Docker integrado na `main`.
- [ ] PR do agente e da API integrado na `main`.
- [ ] `.env.example` unico e coerente.
- [ ] Versoes do InfluxDB e Grafana fixadas.
- [ ] Limites de recursos do Docker definidos.
- [ ] Contrato de campos e unidades congelado.
- [ ] Pipeline iniciado por um unico comando.
- [ ] Agente enviando continuamente a cada 60 segundos.
- [ ] Datasource do Grafana provisionado automaticamente.
- [ ] Dashboard de CPU funcionando.
- [ ] Dashboard de memoria funcionando.
- [ ] Dashboard de disco funcionando.
- [ ] Status da ultima coleta funcionando.
- [ ] Filtros de host e ambiente funcionando.
- [ ] Recuperacao da fila do agente validada.
- [ ] Reinicio dos containers validado sem perda de dados.
- [ ] README com operacao local concluido.
- [ ] Teste final reproduzivel aprovado.

## 6. Fora do MVP

Estes itens permanecem importantes, mas nao bloqueiam a definicao atual de pronto:

- deploy e supervisao no servidor Linux;
- `systemd` e configuracao de producao;
- bot do Telegram;
- collector real para GPU AMD;
- temperatura real no macOS;
- alertas e notificacoes externas;
- GitHub Actions;
- HTTPS, dominio, VPN e reverse proxy;
- backup operacional de producao;
- deteccao de anomalias e previsao;
- suporte a varias organizacoes ou usuarios.

## 7. Proxima acao

A proxima entrega deve consolidar as branches Docker e agente em uma base de integracao,
resolver o `.env.example` e executar os testes. Somente depois disso deve ser iniciado o
dashboard, usando o contrato definitivo das metricas persistidas.
