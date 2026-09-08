# Backend - API de Inferência de Preços de Imóveis

API construída em **FastAPI** para servir previsões em tempo real do modelo de regressão (XGBoost/Scikit-Learn) treinado pelo `ml-worker` e publicado no **Hugging Face Hub**.

---

## 🚀 Arquitetura e Decisões de Engenharia

- **Lifespan Manager Assíncrono (`@asynccontextmanager`)**: O modelo é baixado do Hugging Face Hub (usando `hf_hub_download`) e carregado na memória RAM apenas uma vez no boot da aplicação via `joblib.load()`.
- **Cache Local do Hugging Face**: O Hub verifica as ETags e hashes do commit. Downloads subsequentes ou reinicializações locais/Render utilizam o cache em disco instantaneamente.
- **Zero Overhead & Alta Concorrência**: Não há filas externas pesadas (sem Celery/Redis). O modelo é *read-only* na memória e o FastAPI despacha as inferências no pool de threads interno, consumindo o mínimo de memória do tier gratuito/básico do Render.
- **CORS Configurado**: Pronto para receber requisições do frontend React/Next.js.

---

## 🛠️ Configuração de Ambiente (`.env`)

Crie um arquivo `.env` dentro de `apps/backend/` (ou defina no painel de Environment do Render) com base no `.env.example`:

```bash
# Token HF (obrigatório para repositórios privados; opcional se o repo for público)
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx

# ID do repositório no Hugging Face (ex: 'usuario/meu-ape-model')
REPO_ID=usuario/meu-ape-model

# Nome do arquivo do artefato publicado pelo ml-worker
MODEL_FILENAME=model.joblib

# Configurações do Servidor
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=*
```

---

## 💻 Execução Local

A partir da raiz do monorepo:

```bash
# Iniciar a API com reload automático
uv run uvicorn apps.backend.src.main:app --reload --port 8000
```

Ou entrando na pasta `apps/backend`:

```bash
cd apps/backend
uv run uvicorn src.main:app --reload --port 8000
```

Documentação interativa Swagger disponível em: `http://localhost:8000/docs`

---

## 🧪 Testes Automatizados

Para rodar a suíte de testes da API:

```bash
uv run pytest apps/backend/tests -v
```

---

## 📝 Onde preencher as features e o DataFrame (TODOs)

1. **Adicionar as ~30 features no Schema Pydantic:**
   Abra [`apps/backend/src/schemas.py`](file:///home/gauloish/.dev/ds/projects/meu-ape/apps/backend/src/schemas.py) e localize a classe `ImovelInferenceRequest` no bloco marcado com `# TODO: Adicione as demais features aqui`.

2. **Injetar a lógica de conversão para DataFrame:**
   Abra [`apps/backend/src/routers/prediction.py`](file:///home/gauloish/.dev/ds/projects/meu-ape/apps/backend/src/routers/prediction.py) e localize a função `request_to_dataframe` no bloco marcado com `# TODO: Injetar a lógica de construção do DataFrame a partir do request`.
