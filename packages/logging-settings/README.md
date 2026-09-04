# Logging Settings (`logging-settings`)

Pacote interno do monorepo **meu-ape** contendo utilitários e formatação personalizada de *logging* com suporte a cores para terminal.

---

## Funcionalidades

- **`ColorFormatter`**: Formatador estendido de `logging.Formatter` que aplica cores ANSI nos níveis de log para facilitar a leitura no console durante o desenvolvimento.
  - `DEBUG`: Cinza
  - `INFO`: Azul
  - `WARNING`: Amarelo
  - `ERROR`: Vermelho
  - `CRITICAL`: Vermelho em Negrito
- **`setup_logger`**: Função utilitária para inicializar e configurar handlers de log padrão de forma rápida e padronizada em aplicações e pacotes do monorepo.

---

## Instalação (Monorepo `uv`)

Para utilizar o `logging-settings` em uma aplicação (`apps/`) ou outro pacote (`packages/`), adicione a dependência via `uv`:

```bash
uv add logging-settings --package <nome-do-app-ou-pacote>
```

Ou declare diretamente no `pyproject.toml`:

```toml
[project]
dependencies = [
    "logging-settings",
]
```

---

## Exemplo de Uso

### Configuração Rápida via `setup_logger`

```python
from logging_settings import setup_logger

# Inicializa o logger com nível INFO e suporte a cores no console
logger = setup_logger("meu_app", level="INFO")

logger.info("Aplicação iniciada com sucesso.")
logger.warning("Atenção: parâmetro opcional não fornecido.")
logger.error("Ocorreu uma falha ao conectar ao serviço.")
```

### Uso Personalizado do `ColorFormatter`

```python
import logging
import sys
from logging_settings import ColorFormatter

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColorFormatter())

logger = logging.getLogger("custom_logger")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

logger.debug("Mensagem de depuração.")
```

---

## Estrutura de Arquivos

```text
packages/logging-settings/
├── pyproject.toml
├── README.md
└── src/
    └── logging_settings/
        ├── __init__.py
        ├── formatter.py
        └── setup.py
```
