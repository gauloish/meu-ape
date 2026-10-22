# Backend — API de Inferência de Preços de Imóveis

API HTTP desenvolvida em FastAPI responsável por servir previsões de preços de venda de imóveis em Goiânia (GO), utilizando o modelo de Machine Learning treinado pelo `ml-worker` e disponibilizado no Hugging Face Hub.

---

## Visão Geral

O backend atua como a camada de serviço e inferência online do projeto Meu Apê. Suas principais responsabilidades são:

- Gerenciar o ciclo de vida do modelo preditivo em memória via `FastAPI Lifespan`.
- Baixar e atualizar o artefato do modelo (`model.joblib`) a partir do Hugging Face Hub com cache local em disco.
- Validar contratos de entrada e saída por meio de schemas Pydantic v2, aplicando limites numéricos e restrições geográficas para Goiânia.
- Transformar os dados recebidos em `pandas.DataFrame` estruturado para inferência pelo estimador XGBoost / scikit-learn.
- Expor endpoints HTTP para verificação de disponibilidade (`GET /health`) e predição de preços (`POST /predict`).

---

## Arquitetura da Aplicação

### Organização dos Módulos

```
apps/backend/
├── src/
│   ├── main.py             # Inicialização da aplicação FastAPI, CORS e lifespan
│   ├── config.py           # Configurações e variáveis de ambiente via Pydantic Settings
│   ├── dependencies.py     # Injeção de dependência do modelo (validação de disponibilidade)
│   ├── schemas.py          # Schemas de validação de entrada, saída e limites geográficos
│   └── routers/
│       ├── health.py       # Endpoint de integridade (GET /health)
│       └── prediction.py   # Endpoint de inferência (POST /predict)
├── tests/                  # Suíte de testes unitários e de integração HTTP
├── Dockerfile              # Imagem de produção baseada em python:3.12-slim
├── docker-compose.yml      # Definição do serviço conteinerizado
└── Taskfile.yml            # Automação de comandos de build, execução e testes
```

### Fluxo de Execução

1. **Inicialização (`lifespan`)**: No boot do servidor, a função `load_model_from_hub()` baixa ou reaproveita o artefato em cache do Hugging Face Hub e o carrega em memória em `app.state.model`. Caso o repositório não esteja configurado ou ocorra falha de rede, a aplicação inicializa com o modelo nulo sem abortar o processo.
2. **Atendimento de Requisições (`/predict`)**:
   - O payload JSON é validado pelo schema `InferenceRequest`.
   - A dependência `get_model` recupera a instância em memória; se o modelo não estiver carregado, retorna `HTTP 503`.
   - A função `request_to_dataframe` converte a requisição em um `pandas.DataFrame` de 36 features (tipo do imóvel, 5 atributos numéricos, 28 amenidades booleanas e 2 coordenadas geográficas).
   - O estimador executa a predição e o valor estimado é retornado em formato JSON com código `HTTP 200`.

---

## Configuração e Requisitos

### Requisitos de Software

- Python `>=3.12`
- Gerenciador de pacotes `uv`
- Ferramenta de automação de tarefas `task` (Taskfile)
- Docker e Docker Compose

### Variáveis de Ambiente

As configurações são definidas no arquivo `.env` dentro de `apps/backend/` ou via variáveis de ambiente:

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `REPO_ID` | `str` | `""` | Repositório no Hugging Face Hub (ex: `usuario/meu-ape`). |
| `MODEL_FILENAME` | `str` | `"model.joblib"` | Nome do artefato serializado no Hugging Face Hub. |
| `HF_TOKEN` | `str \| None` | `None` | Token de autenticação da Hugging Face (obrigatório para repositórios privados). |
| `HF_CACHE_DIR` | `Path \| None` | `None` | Diretório customizado para cache de downloads do Hugging Face. |
| `HOST` | `str` | `"0.0.0.0"` | Endereço de bind do servidor Uvicorn. |
| `PORT` | `int` | `8000` | Porta TCP do servidor HTTP. |
| `LOG_LEVEL` | `str` | `"INFO"` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `CORS_ORIGINS` | `str` | `"*"` | Origens permitidas para requisições cross-origin (separadas por vírgula ou `*`). |

---

## Execução e Testes com Taskfile

Todas as operações de execução da aplicação e da suíte de testes são centralizadas no `Taskfile.yml`.

Os comandos podem ser executados a partir da raiz do monorepo (com `-d apps/backend`) ou diretamente dentro da pasta `apps/backend`:

### Execução da Aplicação (Docker)

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/backend run` | Reconstrói a imagem Docker e sobe a infraestrutura completa |
| `task -d apps/backend up` | Sobe os contêineres Docker em background |
| `task -d apps/backend down` | Encerra e remove os contêineres e redes |
| `task -d apps/backend logs` | Exibe os logs da API em tempo real |
| `task -d apps/backend ps` | Exibe o status dos contêineres |
| `task -d apps/backend shell` | Abre um terminal interativo no contêiner da aplicação |
| `task -d apps/backend clean` | Remove contêineres, volumes e imagens locais |
| `task -d apps/backend reset` | Limpa o ambiente e recria a infraestrutura do zero |

### Testes e Qualidade de Código

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/backend test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d apps/backend test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d apps/backend lint` | Executa a verificação estática de código com o `ruff` |
| `task -d apps/backend format` | Verifica a formatação do código com o `ruff` |
| `task -d apps/backend verify` | Executa a checagem de tipos estáticos com o `ty` |

---

## Endpoints da API

Com a aplicação em execução, a documentação interativa fica disponível em:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 1. Verificação de Integridade (`GET /health`)

Retorna o estado operacional da API e a disponibilidade do modelo de Machine Learning na memória.

**Exemplo de Resposta (`HTTP 200 OK`):**

```json
{
  "status": "healthy",
  "model_loaded": true
}
```

---

### 2. Previsão de Preço (`POST /predict`)

Calcula a estimativa de preço de venda de um imóvel com base nas suas características.

#### Parâmetros da Requisição (`InferenceRequest`)

- **Campos Obrigatórios**:
  - `tipo_imovel` (`str`): Categoria do imóvel (`"apartamento"`, `"casa"`, `"cobertura"`, `"sobrado"`, `"flat"`, `"studio"`, `"outro"`).
  - `condominio` (`int`): Valor mensal do condomínio em R$ (entre `0` e `5000`).
  - `area_m2` (`int`): Área útil do imóvel (entre `20` e `1000` m²).
  - `quartos` (`int`): Quantidade de quartos (entre `0` e `8`).
  - `banheiros` (`int`): Quantidade de banheiros (entre `0` e `8`).
  - `vagas` (`int`): Quantidade de vagas de garagem (entre `0` e `8`).
- **Campos Opcionais**:
  - `latitude` (`float`): Latitude dentro dos limites de Goiânia (`-16.85` a `-16.55`). Padrão: `NaN`.
  - `longitude` (`float`): Longitude dentro dos limites de Goiânia (`-49.45` a `-49.15`). Padrão: `NaN`.
  - 28 variáveis booleanas de amenidades (padrão `false`): `piscina`, `academia`, `espaco_gourmet`, `portaria`, `seguranca`, `varanda`, `moveis_embutidos`, `acabamento_premium`, entre outras.

#### Exemplo de Requisição

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_imovel": "apartamento",
    "condominio": 650,
    "area_m2": 85,
    "quartos": 3,
    "banheiros": 2,
    "vagas": 2,
    "piscina": true,
    "academia": true,
    "portaria": true,
    "latitude": -16.6868,
    "longitude": -49.2648
  }'
```

#### Exemplo de Resposta (`HTTP 200 OK`)

```json
{
  "estimated_price": 785000.0,
  "currency": "BRL"
}
```

#### Códigos de Status HTTP

| Código | Condição |
| :--- | :--- |
| `200 OK` | Inferência calculada com sucesso. |
| `422 Unprocessable Entity` | Dados inválidos (campos obrigatórios ausentes, coordenadas fora de Goiânia ou valores numéricos fora dos limites). |
| `500 Internal Server Error` | Erro durante a execução da predição pelo estimador. |
| `503 Service Unavailable` | Modelo de Machine Learning não carregado na memória ou em inicialização. |
