FROM python:3.12-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root system user for security
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Espelha a estrutura do monorepo no contêiner
WORKDIR /monorepo

COPY pyproject.toml uv.lock* ./

# 1. Copia o pacote local primeiro (para aproveitar o cache caso ele não mude)
COPY packages/logging-config/ ./packages/logging-config/

# 2. Copia APENAS o arquivo de dependências da aplicação
# Como o contexto de build é a raiz (../../), especificamos o caminho completo
COPY apps/geocoding-api/pyproject.toml ./apps/geocoding-api/

# Muda para a pasta da aplicação para rodar a instalação
WORKDIR /monorepo/apps/geocoding-api

# 3. Instala as dependências.
# O uv lerá o caminho ../../packages/logging-config e o encontrará perfeitamente
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# 4. Copia o restante do código da aplicação
COPY apps/geocoding-api/ ./

# Ajusta as permissões para o usuário não-root (em todo o monorepo)
RUN chown -R appuser:appgroup /monorepo

USER appuser

EXPOSE 8000

# O WORKDIR já é /monorepo/apps/geocoding-api, então o uvicorn achará o src.main
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]