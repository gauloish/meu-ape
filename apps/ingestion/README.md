# Ingestion — Coleta Diária de Anúncios do Zap Imóveis

Aplicação de linha de comando responsável por coletar anúncios de venda de imóveis em Goiânia (GO) no portal Zap Imóveis, remover duplicatas do mesmo imóvel físico e sincronizar os novos registros com o banco PostgreSQL remoto.

---

## Visão Geral

A ingestion alimenta a base de dados usada pelo restante do projeto Meu Apê. Suas principais responsabilidades são:

- Percorrer as buscas do portal particionadas por categoria de imóvel e faixa de preço, mantendo cada partição abaixo do limite de páginas do site.
- Extrair os anúncios dos blocos estruturados JSON-LD das páginas e normalizá-los em registros tabulares.
- Simular um navegador real (impersonação TLS do Chrome via `curl_cffi`), com aquecimento de sessão e backoff para respostas `429` e `403`.
- Salvar o progresso em CSV de forma incremental (checkpoint), permitindo retomar coletas interrompidas.
- Identificar anúncios de imobiliárias diferentes que se referem ao mesmo imóvel e manter apenas o registro mais completo.
- Persistir apenas anúncios inéditos na tabela `listings` via SQLAlchemy.

---

## Arquitetura da Aplicação

### Organização dos Módulos

```
apps/ingestion/
├── main.py                      # Ponto de entrada da CLI
├── src/
│   ├── cli/main.py              # Definição dos subcomandos (argparse)
│   ├── scraping/
│   │   ├── config.py            # URL base, categorias, faixas de preço e cabeçalhos
│   │   ├── http_client.py       # Clientes HTTP síncrono e assíncrono com retentativas
│   │   ├── zap_parser.py        # Normalização dos itens JSON-LD em registros
│   │   ├── zap_scraper_async.py # Coleta assíncrona (usada na rotina diária)
│   │   └── zap_scraper_sync.py  # Coleta síncrona multi-thread
│   ├── data/
│   │   ├── checkpoint.py        # Persistência incremental em CSV com deduplicação por ID
│   │   ├── deduplicator.py      # Deduplicação por assinatura do imóvel físico
│   │   └── validator.py         # Comparação de cobertura com os totais do portal
│   ├── database/                # Engine, sessão, modelo `Listing` e `ListingRepository`
│   └── pipeline/
│       ├── daily_scrape.py      # Orquestração da rotina diária
│       └── load_csv.py          # Carga em lote de um CSV existente
├── tests/                       # Suíte de testes unitários (sem rede e sem banco real)
└── Taskfile.yml                 # Automação de comandos de execução e testes
```

### Fluxo da Rotina Diária (`daily-scrape`)

1. **IDs conhecidos**: carrega do banco todos os `listing_id` já persistidos. Se o banco estiver indisponível, segue sem esse filtro.
2. **Coleta**: percorre cada partição (categoria × faixa de preço) até `--max-pages` páginas. A paginação de uma partição é interrompida quando uma página (a partir da segunda) contém apenas anúncios já conhecidos. O resultado é salvo em `data/raw/zap_daily_AAAAMMDD.csv`.
3. **Deduplicação física**: gera `data/processed/zap_daily_AAAAMMDD_dedup.csv`, mantendo por assinatura (rua + área + quartos + preço, ou bairro + tipo + atributos quando não há rua) o anúncio com mais informações.
4. **Persistência**: insere no banco apenas os IDs ainda inexistentes. Com `--dry-run`, esta etapa é ignorada.

Os caminhos `data/` são relativos ao diretório de execução (por padrão, `apps/ingestion/`).

---

## Configuração e Requisitos

### Requisitos de Software

- Python `>=3.12`
- Gerenciador de pacotes `uv`
- Ferramenta de automação de tarefas `task` (Taskfile)

### Variáveis de Ambiente

As configurações são definidas no arquivo `.env` dentro de `apps/ingestion/` ou via variáveis de ambiente:

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `str \| None` | `None` | URL de conexão do PostgreSQL. Os esquemas `postgres://` e `postgresql://` são convertidos automaticamente para `postgresql+psycopg://`. Sem ela, é usado um SQLite local em `artifacts/geocoder/cache/geocoding.db`. |

---

## Execução e Testes com Taskfile

Os comandos podem ser executados a partir da raiz do monorepo (com `-d apps/ingestion`) ou diretamente dentro da pasta `apps/ingestion`:

### Coleta e Carga de Dados

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/ingestion daily` | Executa a rotina diária completa (coleta, deduplicação e gravação no banco) |
| `task -d apps/ingestion daily-dry` | Executa a rotina diária sem gravar no banco |
| `task -d apps/ingestion scrape` | Executa a coleta completa assíncrona de todas as partições |
| `task -d apps/ingestion deduplicate` | Remove duplicatas físicas de `data/raw/zap_dataset.csv` |
| `task -d apps/ingestion load-csv` | Carrega um CSV existente no banco (caminho via `INPUT=...`) |
| `task -d apps/ingestion validate` | Compara a cobertura do dataset local com os totais do portal |

As tarefas `daily`, `daily-dry` e `scrape` aceitam `CONCURRENCY` (padrão `1`), e as duas primeiras também `MAX_PAGES` (padrão `10`):

```bash
CONCURRENCY=2 MAX_PAGES=5 task -d apps/ingestion daily-dry
```

Para carregar o dataset histórico versionado na raiz do repositório:

```bash
INPUT=../../data/processed/zap_dataset_deduplicated.csv task -d apps/ingestion load-csv
```

A CLI também pode ser usada diretamente: `uv run python main.py --help`.

### Testes e Qualidade de Código

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/ingestion test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d apps/ingestion test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d apps/ingestion lint` | Executa a verificação estática de código com o `ruff` |
| `task -d apps/ingestion format` | Verifica a formatação do código com o `ruff` |
| `task -d apps/ingestion verify` | Executa a checagem de tipos estáticos com o `ty` |

---

## Execução Agendada (GitHub Actions)

O workflow [`.github/workflows/daily_scrape.yml`](../../.github/workflows/daily_scrape.yml) executa `daily-scrape` todos os dias às 09:00 UTC (06:00 BRT), e também pode ser disparado manualmente (`workflow_dispatch`). A URL do banco é lida do secret `DATABASE_URL` do repositório.
