# Plano de acao - Controller e seguranca da API

## Objetivo

Consolidar as rotas HTTP do Sentinela em um controller de monitoramento e proteger o fluxo ETL
contra escrita nao autorizada, excesso de requisicoes, payloads abusivos, crescimento ilimitado
do buffer e exposicao de informacoes internas.

Esta entrega nao cria autenticacao de usuarios. As chaves implementadas identificam servicos:
coletores autorizados a escrever e consumidores autorizados a consultar metricas.

## Arquitetura alvo

```text
Collector -> POST /metrics -> Controller -> Services -> Buffer -> InfluxDB
Telegram  -> rotas de leitura -> Controller -> Services
Grafana   -> InfluxDB
```

O controller deve cuidar apenas do protocolo HTTP: schemas, dependencias de seguranca, limites
de requisicao, status codes e encaminhamento para services. Transformacao, buffer e
persistencia permanecem fora dele.

## Plano de execucao

### Fase 1 - Consolidacao do controller

- [x] criar `Controllers/monitoring_controller.py`;
- [x] reunir healthcheck, ingestao e consultas de hardware;
- [x] preservar todas as URLs atuais;
- [x] remover os dois controllers substituidos;
- [x] deixar `main.py` responsavel somente pela aplicacao e middlewares.

### Fase 2 - Validacao de entrada

- [x] mover o payload para `Schemas/metric_schema.py`;
- [x] rejeitar campos desconhecidos;
- [x] limitar measurement, tags, fields e strings;
- [x] aceitar apenas tipos compativeis com o InfluxDB;
- [x] restringir measurements permitidos;
- [x] exigir `application/json` na escrita;
- [x] rejeitar corpos maiores que 32 KiB com HTTP 413.

### Fase 3 - Protecao entre servicos

- [x] exigir uma chave de ingestao em `POST /metrics`;
- [x] exigir uma chave de leitura nas rotas de hardware;
- [x] manter `GET /health` publico;
- [x] comparar chaves em tempo constante;
- [x] falhar de forma fechada quando as chaves nao estiverem configuradas;
- [x] manter os segredos somente no `.env` local.

### Fase 4 - Controle de recursos

- [x] limitar ingestao por IP;
- [x] limitar consultas por IP;
- [x] limitar healthchecks por IP;
- [x] responder HTTP 429 e `Retry-After` quando o limite for excedido;
- [x] limitar a quantidade de metricas mantidas no buffer;
- [x] responder HTTP 503 quando o buffer estiver cheio;
- [x] definir timeout para conexoes com o InfluxDB.

### Fase 5 - Hardening HTTP e dados

- [x] fechar CORS por padrao;
- [x] permitir somente hosts configurados;
- [x] adicionar headers de seguranca e `no-store`;
- [x] permitir redirecionamento HTTPS por configuracao;
- [x] permitir desativar Swagger e OpenAPI em producao;
- [x] nao devolver mensagens internas do InfluxDB ou do sistema operacional;
- [x] fechar o cliente do InfluxDB no encerramento da API.

### Fase 6 - Validacao e publicacao

- [x] testar chaves validas, ausentes e invalidas;
- [x] testar HTTP 413, 415, 422, 429 e 503;
- [x] testar headers, hosts e rotas preservadas;
- [x] executar todos os testes e `pip check`;
- [x] revisar o diff e procurar segredos;
- [x] criar commit e publicar no pull request do projeto.

## Limites iniciais

| Controle | Valor padrao |
| --- | --- |
| ingestao | 30 requisicoes por minuto e por IP |
| leitura | 60 requisicoes por minuto e por IP |
| healthcheck | 120 requisicoes por minuto e por IP |
| corpo HTTP | 32 KiB |
| tags por metrica | 20 |
| fields por metrica | 50 |
| buffer em memoria | 1.000 metricas |
| timeout do InfluxDB | 5 segundos |

Todos os limites operacionais podem ser alterados por variaveis de ambiente.

## Modelo do rate limit

O primeiro deploy usa armazenamento em memoria e deve executar com um unico worker da API. Esse
modo protege a instancia atual sem adicionar outro banco ao MVP.

Quando houver multiplos workers ou replicas, o contador devera ser compartilhado por Redis ou o
rate limit devera ser aplicado no reverse proxy. Contadores em memoria nao sao compartilhados
entre processos e nao substituem firewall, TLS ou limites de rede.

## Criterios de aceite

1. Nenhuma metrica e gravada sem a chave de ingestao correta.
2. Nenhuma rota de hardware responde sem a chave de leitura correta.
3. Um cliente acima do limite recebe HTTP 429 antes de acessar o InfluxDB.
4. Payloads grandes, aninhados ou fora do contrato sao rejeitados.
5. Uma falha do banco nao cresce o buffer indefinidamente.
6. Respostas de erro nao revelam URL, token ou mensagem interna do banco.
7. As rotas existentes continuam registradas no OpenAPI.
8. Configuracoes locais secretas continuam ignoradas pelo Git.

## Referencias tecnicas

- [OWASP REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [Starlette Middleware](https://starlette.dev/middleware/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Standard Library Types](https://pydantic.dev/docs/validation/dev/api/pydantic/standard_library_types/)
- [limits - Quickstart](https://limits.readthedocs.io/en/stable/quickstart.html)

## Resultado da execucao

O plano foi executado na branch `agent/unify-system-collectors` e preservou as oito rotas da
API. O controller foi consolidado, os controles de seguranca foram aplicados e o conjunto
automatizado passou de 10 para 30 testes.

Validacoes finais:

| Verificacao | Resultado |
| --- | --- |
| compilacao dos modulos Python | aprovada |
| `python -m unittest discover -v` | 30 testes aprovados |
| `python -m pip check` | nenhuma dependencia quebrada |
| healthcheck por HTTP real | HTTP 200 |
| leitura por HTTP sem chave | HTTP 401 |
| leitura por HTTP com chave | HTTP 200 |
| 31a ingestao no mesmo minuto | HTTP 429 antes da persistencia |
| payload acima de 32 KiB | HTTP 413 |
| corpo em chunks acima do limite | HTTP 413 |
| host nao permitido | HTTP 400 |
| `.env` | ignorado pelo Git e com permissao local 600 |

As chaves locais foram geradas separadamente com 256 bits de aleatoriedade e nao fazem parte
do repositorio.
