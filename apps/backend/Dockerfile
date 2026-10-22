FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Instala o uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Cria um usuário não-root por segurança
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Cria a pasta do projeto
WORKDIR /repo

# Copia os arquivos de build do uv
COPY pyproject.toml uv.lock* ./

# Copia os pacotes locais do projeto
COPY packages/logging-config/ ./packages/logging-config/
COPY packages/geocoding-client/ ./packages/geocoding-client/
COPY packages/ml-core/ ./packages/ml-core/

# Copia os arquivos de build do backend
COPY apps/backend/pyproject.toml ./apps/backend/

# Muda para a pasta da aplicação para rodar a instalação
WORKDIR /repo/apps/backend

# Instala as dependências do projeto.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# Copia o restante do código da aplicação
COPY apps/backend/ ./

# Ajusta as permissões para o usuário não-root (em todo o repo)
RUN chown -R appuser:appgroup /repo

USER appuser

ENV HOST=0.0.0.0 \
    PORT=8000

EXPOSE ${PORT}

# Executa o backend
CMD ["sh", "-c", "exec uvicorn src.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}"]