# Geocoding Client (`geocoding-client`)

Cliente HTTP em Python assíncrono e síncrono para consumo da API interna de Geocodificação (`apps/geocoding-api`).

---

## Visão Geral

O pacote fornece uma interface fortemente tipada para busca de coordenadas geográficas e endereços reversos, com suporte nativo a requisições em lote (*batch*), autenticação M2M via cabeçalho `X-API-Key` e resiliência com Exponential Backoff via `tenacity` para tratamento automático de *Rate Limit* (`HTTP 429`) e erros temporários de servidor (`HTTP 5xx`).

Suas principais funcionalidades incluem:

- Geocodificação direta individual (`geocode`) e reversa (`reverse_geocode`).
- Operações em lote (`batch_geocode` e `batch_reverse_geocode`) com particionamento automático em sub-lotes de até 100 itens.
- Invólucros síncronos (`*_sync`) para pipelines de dados e scripts analíticos.
- Mapeamento estrito de erros para exceções tipadas derivadas de `GeoAPIError`.

---

## Arquitetura do Pacote

### Organização dos Módulos

```
packages/geocoding-client/
├── src/
│   └── geocoding_client/
│       ├── __init__.py     # Exportações públicas da biblioteca
│       ├── client.py       # Classe principal GeocodingClient (assíncrona e síncrona)
│       ├── config.py       # Configurações do cliente com Pydantic Settings
│       ├── exceptions.py   # Hierarquia de exceções personalizadas (GeoAPIError)
│       ├── schemas.py      # Modelos Pydantic v2 para requisições e respostas
│       └── py.typed        # Marcador PEP 561 para suporte a tipagem estática
├── tests/                  # Suíte de testes unitários com pytest
├── .env.example            # Exemplo de variáveis de ambiente
└── pyproject.toml          # Configuração de dependências e empacotamento
```

---

## Configuração e Requisitos

### Requisitos

- Python `>=3.12`
- Dependências: `httpx>=0.28.1`, `pydantic>=2.13.4`, `pydantic-settings>=2.15.0`, `tenacity>=9.1.4`, `logging-config`

### Variáveis de Ambiente

As configurações são gerenciadas pela classe `ClientSettings` (`geocoding_client.config`):

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `GEO_API_URL` | `str` | `http://localhost:8004` | URL base da API interna de Geocodificação. |
| `GEO_API_KEY` | `str` | `geocoding_secret_key_change_me` | Chave de autenticação M2M enviada via `X-API-Key`. |
| `GEO_TIMEOUT` | `float` | `15.0` | Timeout das requisições em segundos. |
| `GEO_MAX_RETRIES` | `int` | `5` | Número máximo de tentativas do Exponential Backoff em erros 429/5xx. |
| `GEO_BACKOFF_FACTOR` | `float` | `2.0` | Multiplicador de intervalo de backoff exponencial. |

### Integração no Monorepo

No arquivo `pyproject.toml` da aplicação ou pacote consumidor:

```toml
[project]
dependencies = [
    "geocoding-client",
]

[tool.uv.sources]
geocoding-client = { workspace = true }
```

---

## Execução e Testes com Taskfile

Todas as operações de verificação e testes do pacote são automatizadas via `Taskfile.yml`.

Os comandos podem ser executados a partir da raiz do monorepo (com `-d packages/geocoding-client`) ou diretamente dentro da pasta `packages/geocoding-client`:

| Comando | Descrição |
| :--- | :--- |
| `task -d packages/geocoding-client test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d packages/geocoding-client test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d packages/geocoding-client lint` | Executa a verificação estática de código com o `ruff` |
| `task -d packages/geocoding-client format` | Verifica a formatação do código com o `ruff` |
| `task -d packages/geocoding-client verify` | Executa a checagem de tipos estáticos com o `ty` |

---

## Exemplos de Uso e Interfaces

### 1. Uso Assíncrono (`async/await`)

Recomendado para aplicações FastAPI e workers assíncronos:

```python
import asyncio
from geocoding_client import GeocodingClient


async def main():
    async with GeocodingClient() as client:
        # Geocodificação direta
        response = await client.geocode("Avenida Anhanguera, Goiânia")
        if response.data:
            print(response.data.latitude, response.data.longitude)

        # Geocodificação em lote
        batch = await client.batch_geocode(
            ["Praça Cívica, Goiânia", "Av T-63, Goiânia"]
        )
        for item in batch.results:
            if item.data:
                print(item.data.address, item.data.latitude, item.data.longitude)


asyncio.run(main())
```

### 2. Uso Síncrono

Recomendado para pipelines de dados e transformadores do scikit-learn / pandas:

```python
from geocoding_client import GeocodingClient

client = GeocodingClient()

# Busca individual síncrona
res = client.geocode_sync("Avenida Anhanguera, Goiânia")

# Busca em lote síncrona
batch_res = client.batch_geocode_sync(["Praça Cívica, Goiânia", "Av T-63, Goiânia"])

# Busca reversa síncrona
rev_res = client.reverse_geocode_sync(-16.68, -49.25)
```

### 3. Tratamento de Exceções

Hierarquia de exceções derivada de `GeoAPIError`:
- `AuthenticationError` (`HTTP 401`): Chave de API ausente ou inválida.
- `AddressNotFound` (`HTTP 404`): Endereço ou coordenada não localizados.
- `RateLimitExceeded` (`HTTP 429`): Limite de taxa excedido (contém atributo `retry_after`).
- `ServerError` (`HTTP 5xx`): Falha interna no servidor de geocodificação ou Nominatim.
- `HTTPConnectionError`: Falha física de rede ou timeout de conexão.
