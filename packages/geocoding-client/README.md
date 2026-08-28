# Geocoding Client (`geocoding-client`)

Cliente HTTP em Python assíncrono e síncrono para consumo da API interna de Geocodificação (`apps/geocoding-api`).

O pacote fornece uma interface robusta e fortemente tipada (com **Pydantic V2**) para busca de coordenadas geográficas e endereços reversos, contando com suporte nativo a **requisições em lote (batch)**, autenticação M2M via cabeçalho `X-API-Key` e resiliência com **Exponential Backoff** para tratamento automático de *Rate Limit* (HTTP 429) e erros temporários de servidor (HTTP 5xx).

---

## Recursos Principais

- **Assíncrono & Síncrono**: Suporte nativo a `async/await` com `httpx.AsyncClient` e invólucros síncronos (`*_sync`) para scripts e pipelines de dados.
- **Operações em Lote (Batch)**: Métodos otimizados para geocodificar múltiplos endereços ou coordenadas em uma única requisição.
- **Autenticação M2M Segura**: Injeção automática e transparente do cabeçalho `X-API-Key`.
- **Exponential Backoff Nativo**: Retentativas automáticas integradas via `tenacity` com retardo exponencial e *jitter* em caso de limitação de taxa (429) ou indisponibilidade temporária (502/503).
- **Tipagem Estrita**: Modelos de dados e validação de resposta via Pydantic V2.

---

## Instalação / Integração no Monorepo

Como o `geocoding-client` é um pacote do workspace gerenciado via `uv`, basta adicioná-lo ao `pyproject.toml` do seu serviço consumidos (ex: `apps/ml-worker`, `packages/ml-core`):

```toml
[project]
name = "meu-servico"
dependencies = [
    "geocoding-client",
]

[tool.uv.sources]
geocoding-client = { workspace = true }
```

Em seguida, execute a sincronização do workspace:

```bash
uv sync --all-packages
```

---

## Configuração e Variáveis de Ambiente

O cliente utiliza `pydantic-settings` para carregar automaticamente as configurações a partir do arquivo `.env` ou das variáveis de ambiente do sistema:

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `GEO_API_URL` | `str` | `http://localhost:8000` | URL base da API interna de Geocodificação. |
| `GEO_API_KEY` | `str` | `geocoding_secret_key_change_me` | Chave de autenticação M2M enviada no cabeçalho `X-API-Key`. |
| `GEO_TIMEOUT` | `float` | `15.0` | Timeout padrão para requisições em segundos. |
| `GEO_MAX_RETRIES` | `int` | `4` | Número máximo de tentativas do Exponential Backoff em erros 429/5xx. |
| `GEO_BACKOFF_FACTOR` | `float` | `1.5` | Fator multiplicador do intervalo de espera em segundos. |

---

## Exemplos Práticos de Uso

### 1. Uso Assíncrono (`async/await`)

Recomendado para aplicações FastAPI, workers assíncronos ou serviços de alta concorrência.

```python
import asyncio
from geocoding_client import GeocodingClient, AddressNotFound, RateLimitExceeded

async def main():
    async with GeocodingClient() as client:
        # 1. Geocodificação Direta (Endereço -> Coordenadas)
        try:
            response = await client.geocode("Avenida Anhanguera, Goiânia")
            print(f"Latitude: {response.data.latitude}, Longitude: {response.data.longitude}")
            print(f"Origem do dado: {response.source}")  # 'cache' ou 'nominatim'
        except AddressNotFound:
            print("Endereço não localizado.")

        # 2. Geocodificação Direta em Lote (Batch)
        addresses = [
            "Avenida T-63, Goiânia",
            "Praça Cívica, Goiânia",
            "Avenida 85, Goiânia"
        ]
        batch_res = await client.batch_geocode(addresses)
        for item in batch_res.results:
            print(f"{item.data.address} -> {item.data.latitude}, {item.data.longitude}")

        # 3. Geocodificação Reversa (Coordenadas -> Endereço)
        rev_res = await client.reverse_geocode(latitude=-16.67, longitude=-49.25)
        print(f"Endereço: {rev_res.data}")

        # 4. Geocodificação Reversa em Lote
        coords = [(-16.67, -49.25), (-16.68, -49.26)]
        batch_rev = await client.batch_reverse_geocode(coords)
        for res in batch_rev.results:
            print(f"{res.query.latitude}, {res.query.longitude} -> {res.data}")

        # 5. Verificação de Saúde da API
        health = await client.health_check()
        print(f"Status da API: {health.status} (DB: {health.database}, Nominatim: {health.nominatim})")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 2. Uso Síncrono (Pipelines de Dados / Pandas / Scripts)

Ideal para uso direto em bibliotecas de Machine Learning (`pandas`, `scikit-learn`) ou scripts síncronos:

```python
from geocoding_client import GeocodingClient

client = GeocodingClient()

# Busca individual síncrona
res = client.geocode_sync("Avenida Anhanguera, Goiânia")
print(res.data.formatted_address)

# Busca em lote síncrona (com Exponential Backoff automático sob 429)
batch_res = client.batch_geocode_sync([
    "Avenida T-63, Goiânia",
    "Praça Cívica, Goiânia"
])

for result in batch_res.results:
    print(result.data.latitude, result.data.longitude)

# Encerramento das conexões do cliente HTTP
import asyncio
asyncio.run(client.close())
```

---

## Tratamento de Exceções

Todas as exceções do pacote herdam de `GeoAPIError`, permitindo um tratamento centralizado ou granular conforme o caso:

```
GeoAPIError (Exceção Base)
├── AuthenticationError     (HTTP 401: API Key ausente ou inválida)
├── AddressNotFound         (HTTP 404: Endereço ou coordenada não localizada)
├── RateLimitExceeded       (HTTP 429: Limite de requisições excedido)
├── ServerError             (HTTP 500/502/503/504: Indisponibilidade de servidor)
└── HTTPConnectionError     (Falha física de rede ou timeout)
```

### Exemplo de Captura de Erros:

```python
from geocoding_client import (
    GeocodingClient,
    AuthenticationError,
    RateLimitExceeded,
    GeoAPIError
)

try:
    client = GeocodingClient()
    result = client.geocode_sync("Endereço Qualquer")
except AuthenticationError:
    print("ERRO: Verifique se a variável GEO_API_KEY está configurada corretamente.")
except RateLimitExceeded as e:
    print(f"ERRO: Limite de taxa excedido. Tente novamente em {e.retry_after} segundos.")
except GeoAPIError as e:
    print(f"ERRO API [{e.status_code}]: {e.message}")
```

---

## Execução dos Testes

Para executar a suíte de testes do pacote dentro do monorepo, utilize o comando:

```bash
PYTHONPATH=packages/geocoding-client/src uv run python packages/geocoding-client/tests/test_client.py
```
