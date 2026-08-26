# Geocoding API

API RESTful de alta performance para geocodificação (conversão de endereços em coordenadas) e geocodificação reversa (conversão de coordenadas em endereços). 

Desenvolvida com **FastAPI**, a aplicação utiliza uma instância dedicada do **Nominatim** para processamento geoespacial e um banco de dados **PostgreSQL** como camada de cache persistente de baixa latência. Essa arquitetura desacopla a aplicação de APIs pagas externas e garante respostas em milissegundos para requisições repetidas.

---

## Features Principais

- **Geocodificação Direta (Encoder):** Conversão de endereços em coordenadas geográficas (`latitude`, `longitude`).
- **Geocodificação Reversa (Decoder):** Identificação de endereços formatados a partir de pares de coordenadas.
- **Processamento em Lote (Batch):** Endpoints otimizados (`/geocoding/search/batch` e `/geocoding/reverse/batch`) que utilizam concorrência assíncrona (`asyncio.gather` com semáforo) para acelerar a resolução de múltiplos itens.
- **Cache de Alta Performance em PostgreSQL:** Armazenamento automático de buscas prévias. Requisições idênticas são servidas diretamente pelo banco com indicação da origem (`"source": "cache"`), reduzindo drasticamente a carga no Nominatim.
- **Diagnóstico Ativo (Health Check):** Endpoint `/health` que realiza verificações reais de conectividade com o PostgreSQL e com o servidor Nominatim.

---

## Stack Tecnológica

- **Linguagem & Framework:** Python 3.12+ / FastAPI
- **Gerenciamento de Pacotes:** [uv](https://github.com/astral-sh/uv) (Workspaces Monorepo)
- **Banco de Dados (Cache):** PostgreSQL 15 com SQLAlchemy 2.0 (Asyncpg)
- **Servidor Geoespacial:** Nominatim 5.3 (mediagis/nominatim)
- **Cliente HTTP Assíncrono:** HTTPX (com pool de conexões compartilhado)
- **Orquestração & Infraestrutura:** Docker, Docker Compose, Task (Taskfile)

---

## Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas em sua máquina local:

- **Docker:** Versão 24.0+
- **Docker Compose:** Versão 2.20+
- **uv:** Gerenciador de projetos Python (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Task:** Task runner simples para orquestração de comandos (`https://taskfile.dev`)

---

## Instruções de Execução (Quickstart)

> **Nota:** Todos os comandos abaixo devem ser executados a partir do diretório do microsserviço: `apps/geocoding-api`.

### 1. Configurar Variáveis de Ambiente

Crie o arquivo `.env` com base no modelo fornecido:

```bash
cp .env.example .env
```

*Os valores padrão já estão pré-configurados para o ambiente de desenvolvimento local.*

### 2. Baixar os Dados do Mapa e Iniciar a Infraestrutura

Utilize o `Taskfile` para executar o fluxo completo de preparação e subida dos contêineres:

```bash
task run
```

O comando `task run` realiza automaticamente:
1. Download e corte do recorte geográfico do OpenStreetMap (OSM) via script local.
2. Construção e inicialização dos contêineres Docker (`web_api`, `nominatim_server` e `cache_db`).

### 3. Comandos Úteis do Taskfile

- **Verificar status dos contêineres e health checks:**
  ```bash
  task ps
  ```
- **Visualizar logs da API FastAPI em tempo real:**
  ```bash
  task logs
  ```
- **Parar os contêineres (preservando dados salvos):**
  ```bash
  task down
  ```
- **Limpeza e Reset Total (ambientes zerados de teste):**
  ```bash
  task reset
  ```

---

## Acessando a Documentação

Após subir a infraestrutura, a documentação OpenAPI interativa (Swagger UI) estará disponível em:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Exemplos de Uso (cURL)

### 1. Geocodificação Direta (Busca Única)

```bash
curl -X GET "http://localhost:8000/geocoding/search?address=Praca+do+Trabalhador,+Goiania" \
     -H "accept: application/json"
```

**Resposta de Exemplo (`Cache MISS` - Nominatim):**
```json
{
  "source": "nominatim",
  "data": {
    "place_id": "120973",
    "address": "Praca do Trabalhador, Goiania",
    "latitude": -16.66334,
    "longitude": -49.2617382,
    "formatted_address": "Praça do Trabalhador, Setor Central, Goiânia, Brasil"
  }
}
```

Caso a mesma requisição seja repetida, o retorno utilizará a camada de cache:

**Resposta de Exemplo (`Cache HIT`):**
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

### 2. Geocodificação em Lote (Batch Search)

```bash
curl -X POST "http://localhost:8000/geocoding/search/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "addresses": [
         "Praça do Trabalhador, Goiânia",
         "Parque Vaca Brava, Goiânia"
       ]
     }'
```

**Resposta de Exemplo:**
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

### 3. Geocodificação Reversa (Coordenadas para Endereço)

```bash
curl -X GET "http://localhost:8000/geocoding/reverse?lat=-16.66334&lon=-49.2617382" \
     -H "accept: application/json"
```

---

### 4. Health Check da Aplicação

```bash
curl -X GET "http://localhost:8000/health" \
     -H "accept: application/json"
```

**Resposta de Exemplo:**
```json
{
  "status": "online",
  "message": "Todos os serviços operacionais.",
  "database": true,
  "nominatim": true
}
```
