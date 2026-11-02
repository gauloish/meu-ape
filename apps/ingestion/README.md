# Ingestion — Módulo de Ingestão, Histórico de Preços e Sincronização com PostgreSQL

Aplicação de linha de comando responsável pela ingestão de dados de imóveis residenciais e comerciais em Goiânia (GO), deduplicação em três níveis (ID, URL canônica e assinatura física do imóvel), controle de retomada de execução por partição/página, rastreamento de histórico de preços (`listing_price_history`) e atualização monetária pelo índice público **FipeZAP** no PostgreSQL.

---

## Análise Técnica e Limitações de Acesso

### 1. Recursos e Endpoints Públicos Identificados
- **Páginas SSR de Busca Pública**: `https://www.zapimoveis.com.br/{transacao}/{categoria}/{uf}+{cidade}/?pagina={N}&preco-de={min}&preco-ate={max}`
- **Arquivos de Governança e Indexação**: `robots.txt` e sitemaps XML públicos voltados para motores de busca autorizados.
- **Séries Públicas Agregadas**: Relatórios mensais do **Índice FipeZAP (Venda Residencial — Goiânia)** publicados pela Fipe/DataZAP+.

### 2. Estrutura do HTML e Dados Estruturados (`JSON-LD`)
Quando uma página pública responde com HTTP `200 OK`, o HTML inclui blocos `<script type="application/ld+json">` padronizados pelo vocabulário `schema.org`:
- Bloco `@type: "ItemList"` contendo `itemListElement`, onde cada elemento traz um objeto `item` com `@id`, `name`, `additionalType` (`Apartment`, `House`, `SingleFamilyResidence`), `url`, `offers` (`price`, `priceCurrency`, `additionalProperty` para taxa de condomínio), `address`, `floorSize`, `numberOfBedrooms`/`numberOfRooms`, `numberOfBathroomsTotal`, `petsAllowed`, `amenityFeature`, `image`, `description`, `datePublished` e `dateModified`.
- Tag `<h1>` com o total agregado de anúncios da categoria pesquisada.

### 3. Verificação de API ou Feed Autorizado
- Não há API REST aberta para extração em massa do catálogo de anúncios por terceiros.
- O formato XML do ecossistema Grupo ZAP / CanalPro é um protocolo de **carga (inbound)** utilizado por imobiliárias para publicar seus próprios imóveis, e o **DataZAP+** é comercializado sob licenciamento B2B.
- A fonte pública legítima disponibilizada mensalmente pelo próprio grupo é o **Índice FipeZAP**, integrado em `src/data/price_index.py`.

### 4. Etapa Exata em que Ocorre o Bloqueio
- O bloqueio ocorre na **Camada 1 — Transporte HTTP / Edge WAF (Cloudflare)** (`SyncHttpClient.get`, `AsyncHttpClient.get` e `ZapListingSpider.parse_search_page`), **antes** da extração de HTML/JSON-LD (`extract_listings_from_html`).
- Requisições originadas de IPs de datacenter (como runners do GitHub Actions) ou paginações sequenciais recebem **HTTP `403 Forbidden`** (página de challenge WAF sem JSON-LD `ItemList`) ou **HTTP `429 Too Many Requests`**.

### 5. Limitações Técnicas vs. Restrições Contratuais
- **Limitações Técnicas**: Teto de paginação por consulta (~50 páginas), bloqueio por reputação de ASN/IP em nuvem e rate-limiting ativo na borda (HTTP 403/429).
- **Restrições Contratuais**: Os Termos de Uso do portal vedam coleta automatizada sem autorização prévia e proíbem contornar dispositivos técnicos de controle de acesso. Por esse motivo, este módulo **não implementa** evasão de CAPTCHA, falsificação de TLS fingerprint ou burla de controles anti-bot, operando com fallback automático para a base consolidada de Goiânia (compatível com os 9.267 anúncios) e correção pelo índice público FipeZAP.

---

## Arquitetura da Aplicação

```
apps/ingestion/
├── main.py                        # Ponto de entrada da CLI
├── src/
│   ├── cli/main.py                # Definição dos subcomandos (argparse)
│   ├── scraping/
│   │   ├── config.py              # URL base, categorias, faixas de preço e cabeçalhos
│   │   ├── http_client.py         # Clientes HTTP síncrono e assíncrono com diagnóstico de bloqueio
│   │   ├── zap_parser.py          # Normalização JSON-LD, URL canônica e inspeção de HTML
│   │   ├── zap_scraper_async.py   # Orquestrador assíncrono com retomada por partição/página
│   │   ├── zap_scraper_sync.py    # Orquestrador síncrono multi-thread com retomada
│   │   └── scrapy_spider.py       # Spider Scrapy obedecendo robots.txt e AutoThrottle
│   ├── data/
│   │   ├── checkpoint.py          # Checkpoint incremental em CSV + estado JSON de partições
│   │   ├── deduplicator.py        # Deduplicação por ID, URL canônica e assinatura física
│   │   ├── price_index.py         # Índice FipeZAP Goiânia e resolução de fallback local
│   │   └── validator.py           # Comparação de cobertura com os totais do portal
│   ├── database/
│   │   ├── models.py              # Modelos ORM `Listing` e `ListingPriceHistory`
│   │   ├── repositories.py        # Persistência, deduplicação por ID/URL e histórico de preços
│   │   ├── engine.py              # Configuração SQLAlchemy (PostgreSQL / SQLite fallback)
│   │   └── session.py             # Fábrica de sessões SQLAlchemy
│   └── pipeline/
│       ├── daily_scrape.py        # Orquestração diária com fallback local e FipeZAP
│       └── load_csv.py            # Carga em lote de CSV existente
├── tests/                         # Suíte de testes unitários
└── Taskfile.yml                   # Automação de comandos de execução e testes
```

---

## Comandos Disponíveis (`Taskfile`)

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/ingestion daily` | Executa o pipeline diário (com fallback local caso haja bloqueio HTTP 403/429) |
| `task -d apps/ingestion daily-dry` | Executa o pipeline diário em modo simulação (`--dry-run`) |
| `task -d apps/ingestion scrape` | Executa a coleta assíncrona com retomada de execução |
| `task -d apps/ingestion scrape-scrapy` | Executa o spider Scrapy respeitando `robots.txt` |
| `task -d apps/ingestion apply-index` | Atualiza os preços no banco pelo índice FipeZAP Goiânia e grava histórico |
| `task -d apps/ingestion deduplicate` | Remove duplicatas por ID, URL e assinatura física do imóvel |
| `task -d apps/ingestion load-csv` | Carrega um CSV existente no PostgreSQL (`INPUT=...`) |
| `task -d apps/ingestion test` | Executa a suíte de testes unitários com `pytest` |
| `task -d apps/ingestion lint` | Executa a verificação estática com `ruff` |
| `task -d apps/ingestion verify` | Executa a checagem de tipos com `ty` |
