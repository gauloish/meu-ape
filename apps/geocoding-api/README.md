# Geocoding API — Serviço de Geocodificação e Cache Geoespacial

API RESTful desenvolvida em FastAPI responsável pela conversão bidirecional entre endereços textuais e coordenadas geográficas (latitude e longitude) para a região metropolitana de Goiânia (GO). A aplicação integra um servidor local dedicado Nominatim/OpenStreetMap a uma camada de persistência e cache assíncrono em PostgreSQL.

---

## Visão Geral

A aplicação atua como o microsserviço geoespacial do ecossistema Meu Apê, fornecendo enriquecimento de dados geográficos tanto para o backend de atendimento ao usuário quanto para o pipeline de processamento em lote do worker de Machine Learning.

Suas principais atribuições incluem:

- Geocodificação direta individual (`GET /geocoding/search`) e em lote (`POST /geocoding/search/batch`).
- Geocodificação reversa individual (`GET /geocoding/reverse`) e em lote (`POST /geocoding/reverse/batch`).
- Camada de cache bidirecional em banco de dados PostgreSQL com normalização de strings e índices compostos de coordenadas para latência em milissegundos em requisições recorrentes.
- Autenticação máquina-para-máquina (M2M) via cabeçalho `X-API-Key` segregada em dois níveis de acesso (`app` e `ml`).
- Controle dinâmico de taxa de requisições (*Rate Limiting*) diferenciado por nível de acesso via SlowAPI.
- Diagnóstico de saúde ativo (`GET /health`) com validação de conectividade real com o PostgreSQL e o servidor Nominatim.

---

## Arquitetura da Aplicação

### Organização dos Módulos

```
apps/geocoding-api/
├── src/
│   ├── main.py                 # Inicialização da aplicação FastAPI, CORS, rate limiter e lifespan
│   ├── config.py               # Configurações e variáveis de ambiente via Pydantic Settings
│   ├── dependencies.py         # Injeção de dependências (sessão SQLAlchemy e cliente HTTPX)
│   ├── security.py             # Verificação de chave de autenticação M2M (X-API-Key)
│   ├── rate_limiter.py         # Configuração de limites e resolução de tiers
│   ├── schemas.py              # Modelos Pydantic v2 para contratos de entrada, saída e validação
│   ├── database/
│   │   ├── base.py             # Classe base declarativa do SQLAlchemy
│   │   ├── engine.py           # Configuração de engine assíncrona (Asyncpg) e pooling
│   │   ├── session.py          # Session factory para AsyncSession
│   │   ├── models.py           # Modelos de cache (GeocodingCache e ReverseGeocodingCache)
│   │   └── repositories.py     # Camada de acesso a dados (consultas e upserts em lote)
│   └── routers/
│       ├── health.py           # Endpoint de integridade operacional (GET /health)
│       └── geocoding.py        # Endpoints de busca e resolução geoespacial
├── tests/                      # Suíte completa de testes unitários com pytest
├── scripts/                    # Scripts de automação para download e corte do mapa OSM
├── Dockerfile                  # Imagem de produção baseada em python:3.12-slim
├── docker-compose.yml          # Orquestração do web_api, nominatim_server e cache_db
└── Taskfile.yml                # Automação de infraestrutura, execução e testes
```

### Fluxo de Execução

1. **Autenticação e Rate Limiting**:
   - Cada requisição protegida aos endpoints de `/geocoding/*` valida a presença e validade do cabeçalho `X-API-Key`.
   - Conforme o valor da chave, a requisição é classificada como nível `app` (backend operacional) ou `ml` (processamento massivo), aplicando limites correspondentes de requisições por minuto.
2. **Resolução de Consultas com Estratégia Cache-First**:
   - **Cache HIT**: O repositório consulta o PostgreSQL (por chave normalizada de endereço ou chave composta de coordenadas). Se o registro já existir, retorna o resultado com `"source": "cache"`.
   - **Cache MISS**: A aplicação despacha requisição assíncrona ao servidor Nominatim local via pool HTTPX compartilhado, armazena o resultado no banco com operação de upsert atômica e retorna o payload com `"source": "nominatim"`.
   - **Execução em Lote**: Consultas em lote desduplicam entradas, verificam o cache para todos os itens em uma única query SQL e executam as requisições pendentes ao Nominatim de forma concorrente controlada por semáforo (`asyncio.Semaphore(10)`).

---

## Configuração e Requisitos

### Requisitos de Software

- Python `>=3.12`
- Gerenciador de pacotes `uv`
- Orquestrador de tarefas `task` (Taskfile)
- Docker e Docker Compose

### Variáveis de Ambiente

As configurações são lidas do arquivo `.env` dentro de `apps/geocoding-api/` ou das variáveis injetadas no contêiner:

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `POSTGRES_USER` | `str` | `"user"` | Usuário do banco de dados PostgreSQL. |
| `POSTGRES_PASSWORD` | `str` | `"password"` | Senha de acesso ao PostgreSQL. |
| `POSTGRES_HOST` | `str` | `"cache_db"` | Host do banco de dados (nome do serviço Docker). |
| `POSTGRES_PORT` | `int` | `5432` | Porta TCP do PostgreSQL. |
| `POSTGRES_DB` | `str` | `"geocoding_database"` | Nome da base de dados utilizada para cache. |
| `DB_POOL_SIZE` | `int` | `10` | Tamanho do pool de conexões assíncronas do SQLAlchemy. |
| `DB_MAX_OVERFLOW` | `int` | `20` | Quantidade máxima de conexões extras além do pool. |
| `DB_POOL_RECYCLE` | `int` | `1800` | Tempo em segundos para reciclagem periódica de conexões. |
| `NOMINATIM_URL` | `str` | `"http://nominatim_server:8080"` | URL interna do servidor geoespacial Nominatim. |
| `USER_AGENT` | `str` | `"GeocodingAPI/1.0"` | Header User-Agent utilizado nas chamadas ao Nominatim. |
| `API_PORT` | `int` | `8002` | Porta TCP externa exposta pelo contêiner Docker da API. |
| `LOG_LEVEL` | `str` | `"INFO"` | Nível de log da aplicação (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `GEO_API_KEY_APP` | `str` | `"geocoding_secret_key_change_me"` | Chave de autenticação M2M para o Backend da aplicação. |
| `GEO_API_KEY_ML` | `str` | `"geocoding_ml_secret_key_change_me"` | Chave de autenticação M2M para o pipeline do ML Worker. |
| `RATE_LIMIT_APP_DEFAULT` | `str` | `"60/minute"` | Limite de requisições por minuto para endpoints unitários (Tier App). |
| `RATE_LIMIT_APP_BATCH` | `str` | `"10/minute"` | Limite de requisições por minuto para endpoints em lote (Tier App). |
| `RATE_LIMIT_ML_DEFAULT` | `str` | `"600/minute"` | Limite de requisições por minuto para endpoints unitários (Tier ML). |
| `RATE_LIMIT_ML_BATCH` | `str` | `"120/minute"` | Limite de requisições por minuto para endpoints em lote (Tier ML). |

---

## Execução e Testes com Taskfile

Todas as operações de ciclo de vida e de qualidade de código são gerenciadas via `Taskfile.yml`.

Os comandos podem ser disparados a partir da raiz do monorepo (com `-d apps/geocoding-api`) ou diretamente dentro da pasta `apps/geocoding-api`:

### Execução da Aplicação (Docker)

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/geocoding-api run` | Executa o corte do mapa OSM local e reconstrói/sobe a stack Docker completa |
| `task -d apps/geocoding-api up` | Sobe todos os contêineres Docker em background |
| `task -d apps/geocoding-api build` | Reconstrói a imagem Docker da API e reinicia os serviços |
| `task -d apps/geocoding-api down` | Interrompe e remove os contêineres e redes (preserva volumes de dados) |
| `task -d apps/geocoding-api logs` | Exibe os logs da API FastAPI em tempo real |
| `task -d apps/geocoding-api logs-all` | Exibe os logs de todos os contêineres (API, banco e Nominatim) |
| `task -d apps/geocoding-api ps` | Lista o status e a integridade de todos os contêineres |
| `task -d apps/geocoding-api shell` | Abre um terminal interativo bash dentro do contêiner da API |
| `task -d apps/geocoding-api db-shell` | Conecta via `psql` ao banco de dados PostgreSQL de cache |
| `task -d apps/geocoding-api clean` | Derruba a stack, apaga volumes persistentes e remove imagens locais |
| `task -d apps/geocoding-api reset` | Executa o clean completo e recria o ambiente do zero via `run` |

### Testes e Qualidade de Código

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/geocoding-api test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d apps/geocoding-api test-cov` | Executa a suíte de testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d apps/geocoding-api lint` | Executa verificação estática de código com o `ruff` |
| `task -d apps/geocoding-api format` | Verifica conformidade de formatação de código com o `ruff` |
| `task -d apps/geocoding-api verify` | Executa verificação estática de tipos com o `ty` |

---

## Endpoints da API

Com a aplicação em execução, a documentação interativa fica disponível em:
- Swagger UI: `http://localhost:8002/docs`
- Redoc: `http://localhost:8002/redoc`
- OpenAPI JSON: `http://localhost:8002/openapi.json`

Todos os endpoints sob o prefixo `/geocoding` exigem autenticação via cabeçalho HTTP:
- `X-API-Key: <CHAVE_CONFIGURADA>`

---

### 1. Diagnóstico de Saúde (`GET /health`)

Endpoint público destinado a sondas de liveness e readiness de orquestradores (Docker/Kubernetes). Testa ativamente a conexão com o PostgreSQL (`SELECT 1`) e a rota de status do Nominatim.

**Exemplo de Requisição:**

```bash
curl -X GET "http://localhost:8002/health" -H "accept: application/json"
```

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "status": "online",
  "message": "Todos os serviços operacionais.",
  "database": true,
  "nominatim": true
}
```

Se qualquer dependência falhar, retorna código `HTTP 503 Service Unavailable` com o diagnóstico detalhado no corpo.

---

### 2. Geocodificação Direta Individual (`GET /geocoding/search`)

Converte um endereço textual em coordenadas geográficas (`latitude`, `longitude`).

**Parâmetros de Consulta:**
- `address` (`str`, obrigatório): Endereço a ser geocodificado.

**Exemplo de Requisição:**

```bash
curl -X GET "http://localhost:8002/geocoding/search?address=Praca+do+Trabalhador,+Goiania" \
  -H "accept: application/json" \
  -H "X-API-Key: geocoding_secret_key_change_me"
```

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "source": "cache",
  "data": {
    "place_id": "120973",
    "address": "Praca do Trabalhador, Goiania",
    "latitude": -16.66334,
    "longitude": -49.2617382,
    "formatted_address": "Praça do Trabalhador, Setor Central, Goiânia, Brasil"
  }
}
```

---

### 3. Geocodificação Direta em Lote (`POST /geocoding/search/batch`)

Processa múltiplos endereços em uma única requisição com resolução via cache e chamadas concorrentes ao Nominatim.

**Parâmetros do Corpo (`BatchGeocodingRequest`):**
- `addresses` (`list[str]`, obrigatório): Lista de endereços contendo entre 1 e 500 itens.

**Exemplo de Requisição:**

```bash
curl -X POST "http://localhost:8002/geocoding/search/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: geocoding_secret_key_change_me" \
  -d '{
    "addresses": [
      "Praça do Trabalhador, Goiânia",
      "Parque Vaca Brava, Goiânia"
    ]
  }'
```

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "results": [
    {
      "source": "cache",
      "data": {
        "place_id": "120973",
        "address": "Praça do Trabalhador, Goiânia",
        "latitude": -16.66334,
        "longitude": -49.2617382,
        "formatted_address": "Praça do Trabalhador, Setor Central, Goiânia, Brasil"
      }
    },
    {
      "source": "nominatim",
      "data": {
        "place_id": "981245",
        "address": "Parque Vaca Brava, Goiânia",
        "latitude": -16.70751,
        "longitude": -49.27702,
        "formatted_address": "Parque Vaca Brava, Setor Bueno, Goiânia, Brasil"
      }
    }
  ]
}
```

---

### 4. Geocodificação Reversa Individual (`GET /geocoding/reverse`)

Converte um par de coordenadas geográficas no endereço detalhado correspondente.

**Parâmetros de Consulta:**
- `lat` (`float`, obrigatório): Latitude geográfica (entre `-90.0` e `90.0`).
- `lon` (`float`, obrigatório): Longitude geográfica (entre `-180.0` e `180.0`).

**Exemplo de Requisição:**

```bash
curl -X GET "http://localhost:8002/geocoding/reverse?lat=-16.66334&lon=-49.2617382" \
  -H "accept: application/json" \
  -H "X-API-Key: geocoding_secret_key_change_me"
```

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "source": "nominatim",
  "data": {
    "place_id": 120295,
    "lat": "-16.6632357",
    "lon": "-49.2615261",
    "display_name": "Locomotiva, Avenida Leste-Oeste, Setor Central, Goiânia, 74045-155, Brasil",
    "address": {
      "historic": "Locomotiva",
      "road": "Avenida Leste-Oeste",
      "suburb": "Setor Central",
      "city": "Goiânia",
      "country": "Brasil"
    }
  }
}
```

---

### 5. Geocodificação Reversa em Lote (`POST /geocoding/reverse/batch`)

Processa múltiplos pares de coordenadas em lote.

**Parâmetros do Corpo (`BatchReverseGeocodingRequest`):**
- `coordinates` (`list[CoordinateRequest]`, obrigatório): Lista contendo entre 1 e 500 pares de latitude e longitude.

**Exemplo de Requisição:**

```bash
curl -X POST "http://localhost:8002/geocoding/reverse/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: geocoding_secret_key_change_me" \
  -d '{
    "coordinates": [
      {"latitude": -16.66334, "longitude": -49.2617382},
      {"latitude": -16.70751, "longitude": -49.27702}
    ]
  }'
```

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "results": [
    {
      "query": {
        "latitude": -16.66334,
        "longitude": -49.2617382
      },
      "source": "nominatim",
      "data": {
        "place_id": 120295,
        "display_name": "Locomotiva, Avenida Leste-Oeste, Setor Central, Goiânia, 74045-155, Brasil"
      }
    }
  ]
}
```

---

### Códigos de Retorno HTTP

| Código | Descrição |
| :--- | :--- |
| `200 OK` | Consulta executada com sucesso (via cache ou Nominatim). |
| `401 Unauthorized` | Chave de API ausente ou inválida no cabeçalho `X-API-Key`. |
| `404 Not Found` | Endereço ou coordenada geográfica não encontrada no mapa. |
| `422 Unprocessable Entity` | Parâmetros inválidos (limites numéricos ou coordenadas fora do intervalo válido). |
| `429 Too Many Requests` | Limite de requisições por minuto excedido para o nível de acesso. |
| `502 Bad Gateway` | Falha de comunicação ou timeout com o servidor Nominatim. |
| `503 Service Unavailable` | Banco de dados PostgreSQL ou servidor Nominatim inoperantes. |