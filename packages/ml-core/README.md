# ML Core (`ml-core`)

Biblioteca central de Machine Learning do ecossistema Meu Apê contendo pipelines de pré-processamento, engenharia de características espaciais, transformadores customizados compatíveis com o scikit-learn e estimador regressor baseado em XGBoost com transformação logarítmica de preços.

---

## Visão Geral

O pacote `ml-core` centraliza toda a lógica de preparação de dados e modelagem preditiva utilizada no monorepo (como no `apps/ml-worker` para treinamento contínuo e no `apps/backend` para inferência online).

Suas principais responsabilidades e capacidades são:

- **Pré-processamento de Dados (`preprocessing`)**:
  - Higienização de dados brutos e remoção de duplicados e colunas irrelevantes (`DataCleaner`).
  - Extração de variáveis booleanas de comodidades e refinamento de categorias a partir de texto (`FeatureExtractor`).
  - Enriquecimento espacial vetorizado via cliente HTTP da API de Geocodificação e aplicação de limites geográficos de Goiânia (`GeocodingEnricher`, `DataPreprocessor`).
- **Transformadores Customizados Scikit-Learn (`transformers`)**:
  - `BinsDiscretizer`: discretização de variáveis contínuas em intervalos categóricos pré-definidos.
  - `ClusterTransformer`: clusterização espacial via K-Means com isolamento estrito contra vazamento de dados (*data leakage*).
  - `GeodesicDistanceTransformer`: cálculo vetorizado de distâncias geodésicas (Haversine) até pontos de referência em Goiânia (parques, shoppings, hospitais, faculdades).
  - `RatioTransformer`: cálculo seguro de razões entre variáveis contínuas (ex: preço por m², área por quarto), tratando divisão por zero e infinitos como `NaN`.
- **Estimador Regressor (`estimators`)**:
  - Classe `Regressor` derivada de `BaseEstimator` e `RegressorMixin`, encapsulando `XGBRegressor` envelopado por `TransformedTargetRegressor` e `LogCpTransformer` (`feature-engine`).
  - Proteção nativa contra distorções causadas por imóveis de alto padrão/luxo (outliers na cauda longa).
  - Compatibilidade completa com `sklearn.pipeline.Pipeline`, `cross_validate` e ferramentas de otimização de hiperparâmetros (Optuna).
- **Métricas de Regressão e Validação (`metrics`)**:
  - Modelos fortemente tipados e imutáveis com Pydantic v2 (`RegressionMetrics` e `RegressionMetricsReport`).
  - Cálculo consolidado de R², RMSE, MAE, MedAE, MAPE e erro absoluto máximo.
  - Agregação estatística de folds de validação cruzada (média e desvio padrão).
- **Fábrica de Pipelines (`pipelines`)**:
  - Detecção dinâmica de esquemas de features por tipo de dado (`FeatureGroups`, `get_feature_groups`).
  - Criação de sub-pipelines para colunas numéricas, categóricas, ordinais e booleanas via `ColumnTransformer`.
  - Construção do pipeline unificado de treinamento (`create_training_pipeline`).

---

## Arquitetura do Pacote

### Organização dos Módulos

```
packages/ml-core/
├── src/
│   └── ml_core/
│       ├── __init__.py                          # Exportações públicas da biblioteca
│       ├── py.typed                             # Marcador PEP 561 para tipagem estática
│       ├── preprocessing/                       # Módulos de higienização, extração e geocodificação
│       │   ├── constants.py                     # Constantes de amenidades, tipos de imóvel e limites
│       │   ├── data_cleaning.py                 # Higienização de dados brutos e padronização
│       │   ├── feature_extraction.py            # Extração de amenidades e refinamento de categorias
│       │   ├── geocoding_enrichment.py          # Enriquecimento geográfico vetorizado
│       │   └── data_preprocessor.py             # Pipeline orquestrador de pré-processamento
│       ├── transformers/                        # Transformadores scikit-learn customizados
│       │   ├── bins_discretizer.py              # Discretização por faixas de valores
│       │   ├── cluster_transformer.py           # Clusterização espacial via K-Means
│       │   ├── geodesic_distance_transformer.py # Distâncias geodésicas até pontos de interesse
│       │   └── ratio_transformer.py             # Razões entre atributos numéricos
│       ├── estimators/                          # Estimadores e cálculo de métricas
│       │   ├── estimators.py                    # Estimador Regressor (XGBoost + LogCpTransformer)
│       │   └── metrics.py                       # Modelos Pydantic e funções de métricas
│       └── pipelines/                           # Composição e fábrica de pipelines
│           ├── constants.py                     # Pontos de referência de Goiânia, pares e bins
│           ├── feature_groups.py                # Agrupamento e descoberta dinâmica de colunas
│           └── factory.py                       # Construção de transformadores, preprocessor e pipeline
├── tests/                                       # Suíte completa de testes unitários com pytest
├── pyproject.toml                               # Configuração de dependências e empacotamento
└── Taskfile.yml                                 # Automação de tarefas de teste e qualidade
```

---

## Configuração e Requisitos

### Requisitos

- Python `>=3.12`
- Dependências principais:
  - `feature-engine>=1.9.4`
  - `geocoding-client` (pacote do workspace)
  - `logging-config` (pacote do workspace)
  - `numpy>=2.5.1`
  - `pandas>=3.0.5`
  - `pydantic>=2.13.4`
  - `scikit-learn>=1.9.0`
  - `xgboost>=3.4.1`

### Integração no Monorepo

No arquivo `pyproject.toml` da aplicação consumidora:

```toml
[project]
dependencies = [
    "ml-core",
]

[tool.uv.sources]
ml-core = { workspace = true }
```

---

## Execução e Testes com Taskfile

Todas as operações de verificação e testes do pacote são automatizadas via `Taskfile.yml`.

Os comandos podem ser executados a partir da raiz do monorepo (com `-d packages/ml-core`) ou diretamente dentro da pasta `packages/ml-core`:

| Comando | Descrição |
| :--- | :--- |
| `task -d packages/ml-core test` | Executa a suíte completa de testes unitários com `pytest` via `uv` |
| `task -d packages/ml-core test-cov` | Executa os testes com relatório de cobertura de código (`pytest-cov`) |
| `task -d packages/ml-core lint` | Executa a verificação estática de código com o `ruff` |
| `task -d packages/ml-core format` | Verifica a formatação do código com o `ruff` |
| `task -d packages/ml-core verify` | Executa a checagem de tipos estáticos com o `ty` |

---

## Exemplos de Uso e Interfaces

### 1. Pré-processamento Completo de Dados Brutos

```python
import pandas as pd
from geocoding_client import GeocodingClient
from ml_core.preprocessing import DataPreprocessor

# Instancia o pré-processador com cliente de geocodificação
geo_client = GeocodingClient()
preprocessor = DataPreprocessor(geocoding_client=geo_client)

df_raw = pd.DataFrame(
    {
        "preco": [450000.0],
        "tipo_imovel": ["Apartment"],
        "rua": ["Avenida T-63"],
        "bairro": ["Setor Bueno"],
        "comodidades": ["Pool, Gym, Barbecue Grill"],
        "titulo": ["Apartamento 3 quartos Setor Bueno"],
    }
)

# Executa limpeza, extração de amenidades e enriquecimento de coordenadas
df_cleaned = preprocessor(df_raw)
```

### 2. Criação, Treinamento e Inferência com Pipeline Completo

```python
import pandas as pd
from ml_core.pipelines import create_training_pipeline, get_feature_groups

# Identifica dinamicamente os grupos de colunas
groups = get_feature_groups(X_train)

# Cria a pipeline completa contendo:
# 1. Transformadores (bins, clusters espaciais, distâncias de haversine, razões)
# 2. Preprocessador (imputação e codificação com ColumnTransformer)
# 3. Estimador Regressor (XGBoost com target logarítmico)
pipeline = create_training_pipeline(
    feature_groups=groups,
    n_estimators=100,
    max_depth=5,
    learning_rate=0.05,
    random_state=42,
)

# Ajuste do pipeline
pipeline.fit(X_train, y_train)

# Predição em moeda original (reversão logarítmica automática)
previsoes = pipeline.predict(X_test)
```

### 3. Avaliação de Desempenho e Métricas

```python
from ml_core.estimators import calculate_regression_metrics, RegressionMetricsReport

# Calcula o conjunto padronizado de métricas
metrics = calculate_regression_metrics(y_true=y_test, y_pred=previsoes)

# Exibe o relatório formatado
report = RegressionMetricsReport(regression_metrics=metrics)
print(report.get_report())
# Saída: Métricas(R2: 0.88, RMSE: 35210.45, MAE: 24150.12, MedAE: 18320.00, MAPE: 0.07, Max Error: 89450.00)
```
