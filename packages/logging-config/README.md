# Logging Config (`logging-config`)

Pacote compartilhado do monorepo para padronização e configuração de logs estruturados e coloridos utilizando `loguru`.

---

## Visão Geral

O pacote centraliza a formatação e o direcionamento dos logs de todas as aplicações e pacotes do ecossistema Meu Apê (como `backend`, `ml-worker` e `geocoding-client`).

Suas principais características são:

- Limpeza de sinks padrão do Loguru via `logger.remove()` para evitar duplicação de mensagens.
- Definição de esquema de cores customizado por nível (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- Formatação uniforme contendo módulo, função de origem, data/hora, nível e mensagem de log no `sys.stdout`.

---

## Arquitetura do Pacote

### Organização dos Módulos

```
packages/logging-config/
├── src/
│   └── logging_config/
│       ├── __init__.py     # Exporta a função principal config_logger
│       └── config.py       # Implementação da configuração do Loguru
├── tests/                  # Testes unitários com pytest
└── pyproject.toml          # Metadados e dependências do pacote
```

---

## Configuração e Requisitos

### Requisitos

- Python `>=3.12`
- loguru `>=0.7.3`

### Integração no Monorepo

No arquivo `pyproject.toml` da aplicação consumidora:

```toml
[project]
dependencies = [
    "logging-config",
]

[tool.uv.sources]
logging-config = { workspace = true }
```

---

## Execução e Testes com Taskfile

Todas as operações de verificação e testes do pacote são automatizadas via `Taskfile.yml`.

Os comandos podem ser executados a partir da raiz do monorepo (com `-d packages/logging-config`) ou diretamente dentro da pasta `packages/logging-config`:

| Comando | Descrição |
| :--- | :--- |
| `task -d packages/logging-config test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d packages/logging-config test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d packages/logging-config lint` | Executa a verificação estática de código com o `ruff` |
| `task -d packages/logging-config format` | Verifica a formatação do código com o `ruff` |
| `task -d packages/logging-config verify` | Executa a checagem de tipos estáticos com o `ty` |

---

## Exemplos de Uso

A função `config_logger()` deve ser executada durante a inicialização do serviço ou módulo principal:

```python
from logging_config import config_logger
from loguru import logger

# Inicializa as configurações globais de log
config_logger()

# Emite mensagens padronizadas
logger.info("Aplicação iniciada com sucesso.")
logger.warning("Alerta de processamento.")
logger.error("Erro durante a execução.")
```
