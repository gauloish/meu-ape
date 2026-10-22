# Meu Apê — Plataforma de Precificação de Imóveis em Goiânia

Plataforma orientada a Machine Learning projetada para coleta automatizada, processamento geoespacial, modelagem preditiva e disponibilização de estimativas de preços de venda para o mercado imobiliário residencial de Goiânia (GO).

---

## Visão Geral do Projeto

O objetivo do projeto é acompanhar o mercado imobiliário local de forma contínua e fornecer avaliações precisas de imóveis com base em suas características estruturais, amenidades e localização geográfica.

O ciclo de vida do dado percorre quatro etapas principais:

1. **Ingestão Contínua**: Raspagem programada de anúncios de venda na web e persistência em banco de dados relacional.
2. **Enriquecimento Geoespacial**: Normalização de endereços e resolução de coordenadas com cache local para evitar custos e dependências de APIs proprietárias.
3. **Treinamento e Governança de ML**: Otimização bayesiana de hiperparâmetros, avaliação não-enviesada por validação cruzada aninhada (*Nested CV*) e publicação de artefatos versionados no Hugging Face Hub.
4. **Entrega e Inferência**: Serviço web de baixa latência consumindo o modelo de Machine Learning em memória e interface gráfica para os usuários finais.

---

## Arquitetura do Monorepo

O projeto é estruturado como um monorepo Python gerenciado pelo gerenciador de pacotes **`uv`** (Workspaces) e orquestrado via **Docker** e **Taskfile**. O código é segregado entre aplicações executáveis (`apps/`) e bibliotecas compartilhadas reutilizáveis (`packages/`):

```
meu-ape/
├── apps/
│   ├── ingestion/              # Ingestão periódica via web scraping
│   ├── geocoding-api/          # Microsserviço de geocodificação e cache em PostgreSQL
│   ├── ml-worker/              # Treinamento, otimização e publicação no HF Hub
│   ├── backend/                # API REST de inferência em produção (FastAPI)
│   └── frontend/               # Interface web do usuário (React / TypeScript) [em desenvolvimento]
├── packages/
│   ├── geocoding-client/       # SDK cliente HTTP para consumo da geocoding-api
│   ├── ml-core/                # Pipeline scikit-learn, transformadores e métricas de ML
│   └── logging-config/         # Padronização estruturada de logs com Loguru
├── notebooks/                  # Prototipação, análise exploratória (EDA) e experimentos
├── pyproject.toml              # Definição do workspace uv e dependências raiz
└── README.md                   # Documentação geral do ecossistema
```

---

## Componentes do Sistema

Cada aplicação e pacote do monorepo possui responsabilidade única e conta com seu próprio arquivo `README.md` detalhando arquitetura interna, variáveis de ambiente, comandos de execução e suíte de testes unitários:

### Aplicações (`apps/`)

| Aplicação | Responsabilidade | Documentação |
| :--- | :--- | :--- |
| **`backend`** | API REST desenvolvida em FastAPI que carrega o modelo preditivo XGBoost em memória a partir do Hugging Face Hub e fornece inferência em tempo real via endpoint `POST /predict`. | `apps/backend/README.md` |
| **`geocoding-api`** | Microsserviço FastAPI integrado a uma instância local do Nominatim/OpenStreetMap e cache em PostgreSQL, responsável pela resolução bidirecional entre endereços e coordenadas. | `apps/geocoding-api/README.md` |
| **`ml-worker`** | Worker para execução offline do pipeline de ML. Executa limpeza de dados, Nested Cross-Validation, sintonia com Optuna e upload de artefatos serializados no Hugging Face Hub. | `apps/ml-worker/README.md` |
| **`ingestion`** | Rotina semanal de coleta automatizada de anúncios imobiliários executada via GitHub Actions e armazenada em banco PostgreSQL remoto. | `apps/ingestion/` |
| **`frontend`** | Aplicação web interativa para simulação e visualização de estimativas de imóveis construída com React, TypeScript, HTML e CSS. *(Em desenvolvimento)* | `apps/frontend/` |

### Pacotes Compartilhados (`packages/`)

| Pacote | Responsabilidade | Documentação |
| :--- | :--- | :--- |
| **`ml-core`** | Biblioteca contendo o pré-processador de dados (`DataPreprocessor`), a definição do pipeline scikit-learn (`create_training_pipeline`), o estimador XGBoost e o cálculo de métricas. | `packages/ml-core/README.md` |
| **`geocoding-client`** | Cliente HTTP resiliente (síncrono e assíncrono) com retentativas exponenciais, circuit breaker e pooling para comunicação direta com a `geocoding-api`. | `packages/geocoding-client/README.md` |
| **`logging-config`** | Configuração centralizada e formatada de logging baseada em Loguru utilizada de forma homogênea por todos os componentes do repositório. | `packages/logging-config/README.md` |

---

## Configuração e Requisitos Globais

### Pré-requisitos de Sistema

- **Python `>=3.12`**
- **Gerenciador de Pacotes `uv`**: Ferramenta de alta velocidade para resolução de dependências e workspace (`https://docs.astral.sh/uv/`).
- **Docker e Docker Compose**: Para execução dos contêineres e bancos de dados locais.
- **Task**: Orquestrador de comandos via `Taskfile` (`https://taskfile.dev/`).

### Instalação do Ambiente de Desenvolvimento

Clone o repositório e sincronize o workspace inteiro utilizando o `uv`:

```bash
# Sincroniza todas as dependências do monorepo e pacotes locais em modo editável
uv sync --all-packages
```

O comando criará um ambiente virtual único na raiz (`.venv`) contendo todos os pacotes e aplicações integrados.

---

## Execução e Automação de Tarefas

Cada serviço e biblioteca do monorepo possui seu próprio `Taskfile.yml` com comandos padronizados de desenvolvimento, qualidade e execução:

```bash
# Execução de testes unitários em uma aplicação ou pacote específico
task -d apps/backend test
task -d apps/geocoding-api test
task -d apps/ml-worker test
task -d packages/ml-core test
task -d packages/geocoding-client test
task -d packages/logging-config test

# Verificação estática de código e tipagem
task -d apps/backend lint
task -d apps/backend verify
```

Para subir a infraestrutura completa de microsserviços conteinerizados, consulte as orientações específicas no README de cada aplicação:
- Para a API de inferência: consulte [apps/backend/README.md](file:///home/gauloish/.dev/ds/projects/meu-ape/apps/backend/README.md).
- Para a infraestrutura de geocodificação e mapas: consulte [apps/geocoding-api/README.md](file:///home/gauloish/.dev/ds/projects/meu-ape/apps/geocoding-api/README.md).
- Para o pipeline de treinamento de modelos: consulte [apps/ml-worker/README.md](file:///home/gauloish/.dev/ds/projects/meu-ape/apps/ml-worker/README.md).

---

## Licença

Este projeto está licenciado sob os termos da **Licença MIT**. Consulte o arquivo `LICENSE` para obter mais detalhes.
