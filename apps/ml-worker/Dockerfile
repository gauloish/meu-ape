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

# 1. Copia os pacotes locais primeiro (para aproveitar o cache caso ele não mude)
COPY packages/logging-config/ ./packages/logging-config/
COPY packages/geocoding-client/ ./packages/geocoding-client/
COPY packages/ml-core/ ./packages/ml-core/

# 2. Copia APENAS o arquivo de dependências da aplicação
# Como o contexto de build é a raiz (../../), especificamos o caminho completo
COPY apps/ml-worker/pyproject.toml ./apps/ml-worker/

# Muda para a pasta da aplicação para rodar a instalação
WORKDIR /monorepo/apps/ml-worker

# 3. Instala as dependências.
# O uv lerá o caminho ../../packages/logging-config e o encontrará perfeitamente
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# 4. Copia o restante do código da aplicação
COPY apps/ml-worker/ ./

# Ajusta as permissões para o usuário não-root (em todo o monorepo)
RUN chown -R appuser:appgroup /monorepo

USER appuser

CMD uv run python main.py \
    --mode train \
    --dataset-source $DATASET_SOURCE \
    --n-trials $N_TRIALS \
    --k-folds $K_FOLDS \
    --push-to-hub \
    --repo-id $REPO_ID
