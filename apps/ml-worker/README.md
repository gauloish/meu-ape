# ML Worker — Pipeline de Treinamento, Otimização e Avaliação de Modelos

Aplicação responsável pelo ciclo de vida de Machine Learning no projeto Meu Apê, incluindo pré-processamento de dados brutos, validação cruzada aninhada (*Nested Cross-Validation*), busca bayesiana de hiperparâmetros via Optuna, treinamento do estimador final e publicação automatizada dos artefatos serializados no Hugging Face Hub.

---

## Visão Geral

O `ml-worker` atua como o componente de treinamento offline e experimentação do ecossistema. Ele consome dados tabulares limpos ou brutos (armazenados localmente em formatos Parquet/CSV ou no Hugging Face Hub) e produz um pipeline serializado (`model.joblib`) pronto para consumo em produção pela aplicação de inferência (`apps/backend`).

Suas principais responsabilidades incluem:

- Carregamento flexível de dados a partir do Hugging Face Hub ou de arquivos locais Parquet e CSV.
- Pré-processamento e engenharia de atributos via `DataPreprocessor` do pacote `ml-core`.
- Otimização de hiperparâmetros sem vazamento de dados (*data leakage*) utilizando Optuna com estimador Tree-structured Parzen Estimator (TPE).
- Avaliação não-enviesada de performance por meio de Nested Cross-Validation com loops externo e interno independentes.
- Treinamento do pipeline completo de aprendizado de máquina (`create_training_pipeline`) com 100% dos dados.
- Serialização local dos artefatos (`model.joblib` e `metrics.json`) e publicação versionada no Hugging Face Hub via `HfApi`.

---

## Arquitetura da Aplicação

### Organização dos Módulos

```
apps/ml-worker/
├── src/
│   ├── main.py                 # Interface de Linha de Comando (CLI) e orquestração de modos
│   ├── training/
│   │   ├── __init__.py         # Exportação do módulo de treinamento
│   │   └── train.py            # Carregamento de dados, treino final e upload para o Hugging Face Hub
│   ├── optimization/
│   │   ├── __init__.py         # Exportação do módulo de otimização
│   │   └── optimize.py         # Espaço de busca e otimização bayesiana com Optuna
│   └── evaluation/
│       ├── __init__.py         # Exportação do módulo de avaliação
│       └── evaluate.py         # Avaliação não-enviesada com Nested Cross-Validation (k_outer x k_inner)
├── tests/                      # Suíte completa de testes unitários com pytest
├── artifacts/                  # Diretório local padrão para armazenamento dos modelos e métricas gerados
├── main.py                     # Script de entrada para execução da CLI a partir da raiz do pacote
├── Dockerfile                  # Imagem Docker para execução conteinerizada do treinamento
├── docker-compose.yml          # Configuração de execução via Docker Compose
└── Taskfile.yml                # Automação de execução do treino, infraestrutura e testes
```

### Fluxo de Execução

1. **Ingestão e Pré-processamento**:
   - A função `load_data()` obtém o dataset da fonte especificada (Hugging Face Hub, Parquet ou CSV).
   - O `DataPreprocessor` realiza a limpeza dos dados, tratamento de outliers e engenharia de features, separando a matriz de atributos `X` e a série alvo `y` (`preco`).
   - O particionamento de grupos de atributos (`numeric_features`, `categorical_features`, `boolean_features`) é resolvido dinamicamente via `get_feature_groups()`.
2. **Avaliação por Nested Cross-Validation (se habilitada)**:
   - Os dados são particionados em $k_{outer}$ folds externos.
   - Em cada fold externo, o conjunto de treino é otimizado internamente com $k_{inner}$ folds pelo Optuna.
   - O modelo do fold é avaliado no conjunto de teste externo nunca antes visto pelo otimizador, acumulando métricas de $R^2$, $RMSE$, $MAE$, $MedAE$ e $MAPE$ para cálculo de média e desvio padrão.
3. **Otimização Global e Ajuste Final**:
   - Os hiperparâmetros do modelo regressor XGBoost são sintonizados com o dataset integral utilizando $N_{trials} \times K_{folds}$ iterações.
   - O pipeline final com pré-processador e estimador é ajustado em 100% dos dados.
4. **Exportação e Publicação de Artefatos**:
   - O pipeline treinado é serializado em disco como `artifacts/model.joblib`.
   - O relatório estruturado de métricas e hiperparâmetros é gravado em `artifacts/metrics.json`.
   - Se o flag `--push-to-hub` estiver ativo, os artefatos são transferidos via API para o repositório configurado no Hugging Face Hub.

---

## Configuração e Requisitos

### Requisitos de Software

- Python `>=3.12`
- Gerenciador de pacotes `uv`
- Orquestrador de tarefas `task` (Taskfile)
- Docker e Docker Compose (para execução conteinerizada)

### Variáveis de Ambiente

As variáveis podem ser configuradas no arquivo `.env` dentro de `apps/ml-worker/` ou exportadas no ambiente:

| Variável | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `HF_TOKEN` | `str` | `""` | Token de autenticação da Hugging Face com permissão de escrita. |
| `DATASET_SOURCE` | `str` | `"user/dataset_repo_name"` | Identificador do dataset no HF Hub ou caminho para arquivo local (`.parquet`/`.csv`). |
| `REPO_ID` | `str` | `"user/model_repo_name"` | Repositório no Hugging Face Hub para publicação do modelo (`usuario/nome-do-modelo`). |
| `N_TRIALS` | `int` | `20` | Número de trials para otimização de hiperparâmetros no Optuna. |
| `K_FOLDS` | `int` | `5` | Quantidade de folds para as divisões de Cross-Validation. |
| `GEO_API_KEY` | `str` | `""` | Chave de API para enriquecimento com o microsserviço `geocoding-api` (quando aplicável). |
| `GEO_API_URL` | `str` | `"http://host.docker.internal:8002"` | URL base da Geocoding API para chamadas em lote. |
| `TIMEOUT` | `float` | `15.0` | Timeout em segundos para requisições externas HTTP. |
| `MAX_RETRIES` | `int` | `5` | Número de tentativas automáticas em requisições HTTP externas. |
| `BACKOFF_FACTOR` | `float` | `2.0` | Fator exponencial de espera entre retentativas HTTP. |

---

## Execução do Programa e dos Testes com Taskfile

Todas as operações de treinamento, ciclo de vida de contêineres e testes unitários são centralizadas no `Taskfile.yml`.

Os comandos podem ser executados a partir da raiz do monorepo (com `-d apps/ml-worker`) ou dentro da pasta `apps/ml-worker`:

### Treinamento e Execução Local

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/ml-worker train` | Executa o pipeline completo de treinamento com otimização Optuna e exportação |
| `task -d apps/ml-worker run` | Constrói a imagem Docker e sobe o contêiner do worker |
| `task -d apps/ml-worker up` | Sobe o serviço Docker do worker em segundo plano |
| `task -d apps/ml-worker build` | Reconstrói a imagem Docker do worker |
| `task -d apps/ml-worker down` | Interrompe e remove os contêineres do worker |
| `task -d apps/ml-worker logs` | Exibe os logs de execução do contêiner em tempo real |
| `task -d apps/ml-worker ps` | Exibe o status do contêiner Docker |
| `task -d apps/ml-worker shell` | Abre um terminal interativo bash dentro do contêiner |
| `task -d apps/ml-worker clean` | Remove contêineres, redes e imagens locais do worker |
| `task -d apps/ml-worker reset` | Executa a limpeza e recria o ambiente do zero |

### Testes e Qualidade de Código

| Comando | Descrição |
| :--- | :--- |
| `task -d apps/ml-worker test` | Executa a suíte de testes unitários com `pytest` via `uv` |
| `task -d apps/ml-worker test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d apps/ml-worker lint` | Executa verificação estática de código com o `ruff` |
| `task -d apps/ml-worker format` | Verifica a conformidade de formatação de código com o `ruff` |
| `task -d apps/ml-worker verify` | Executa checagem de tipos estáticos com o `ty` |

---

## Interface de Linha de Comando (CLI)

O ponto de entrada da aplicação é o script `main.py`, que expõe uma CLI configurável com 3 modos de operação:

```bash
uv run python main.py [OPÇÕES]
```

### Argumentos da CLI

| Argumento | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `--mode` | `str` | `"train"` | Modo de operação: `train`, `evaluate` ou `optimize`. |
| `--dataset-source` | `str` | `"user/dataset_repo_name"` | Nome do dataset no HF Hub ou caminho para arquivo local Parquet/CSV. |
| `--n-trials` | `int` | `20` | Quantidade de trials para a busca bayesiana do Optuna. |
| `--k-folds` | `int` | `5` | Número de divisões (folds) para Validação Cruzada. |
| `--push-to-hub` | `flag` | `False` | Quando fornecido, envia os artefatos gerados para o Hugging Face Hub. |
| `--repo-id` | `str` | `None` | Repositório de destino no HF Hub (obrigatório se `--push-to-hub` for ativo). |

---

### Modos de Operação

#### 1. Modo Treinamento (`--mode train`)

Executa o fluxo completo de ponta a ponta: carrega dados, avalia por Nested CV, otimiza hiperparâmetros no dataset total, ajusta o pipeline final em 100% dos dados, grava `model.joblib` e `metrics.json` e realiza o upload para o Hugging Face Hub se solicitado.

```bash
uv run python main.py \
  --mode train \
  --dataset-source "dados/imoveis_goiania.parquet" \
  --n-trials 30 \
  --k-folds 5 \
  --push-to-hub \
  --repo-id "usuario/meu-ape-model"
```

#### 2. Modo Avaliação (`--mode evaluate`)

Executa exclusivamente a Validação Cruzada Aninhada (Nested CV) sem gerar artefato final de produção. O objetivo é mensurar a capacidade de generalização real do pipeline, reportando média e desvio padrão das métricas ($R^2$, $RMSE$, $MAE$, $MedAE$, $MAPE$) livres de viés de otimização.

```bash
uv run python main.py \
  --mode evaluate \
  --dataset-source "dados/imoveis_goiania.parquet" \
  --n-trials 15 \
  --k-folds 5
```

#### 3. Modo Otimização (`--mode optimize`)

Executa apenas a busca de hiperparâmetros no dataset total utilizando o Optuna, exibindo ao término os melhores parâmetros encontrados e o valor mínimo de MAE alcançado na validação cruzada.

```bash
uv run python main.py \
  --mode optimize \
  --dataset-source "dados/imoveis_goiania.parquet" \
  --n-trials 50 \
  --k-folds 5
```

---

### Estrutura dos Artefatos Gerados

Ao término do treinamento, o diretório configurado (`artifacts/`) contém:

1. **`model.joblib`**: Pipeline scikit-learn serializado contendo o `ColumnTransformer` (pré-processamento de atributos numéricos, categóricos e booleanos) e o estimador `Regressor` ajustado.
2. **`metrics.json`**: Metadados estruturados sobre o treinamento realizado:

```json
{
  "best_cv_mae": 32450.75,
  "best_params": {
    "model__n_estimators": 450,
    "model__learning_rate": 0.035,
    "model__max_depth": 6,
    "model__min_child_weight": 3,
    "model__subsample": 0.8,
    "model__colsample_bytree": 0.8,
    "model__reg_alpha": 0.01,
    "model__reg_lambda": 1.5,
    "model__objective": "reg:absoluteerror",
    "model__log_c": 1.0,
    "model__random_state": 1667
  },
  "n_samples": 8420,
  "n_features": 36,
  "evaluation": {
    "metrics_summary": {
      "r2": {"mean": 0.892, "std": 0.018},
      "rmse": {"mean": 54200.10, "std": 3200.40},
      "mae": {"mean": 32450.75, "std": 1850.30},
      "medae": {"mean": 24100.00, "std": 1400.00},
      "mape": {"mean": 0.078, "std": 0.005}
    }
  }
}
```
