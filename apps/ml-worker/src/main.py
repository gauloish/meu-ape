"""Ponto de entrada principal do ml-worker para orquestração de treinamento e avaliação."""

import argparse
import logging
import sys
from pathlib import Path

# Adiciona o diretório 'src' ao sys.path para garantir importações relativas
src_dir = str(Path(__file__).parent.resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from evaluation.evaluate import run_nested_cv
from ml_core.pipelines import get_feature_groups
from optimization.optimize import optimize_hyperparameters
from training.train import load_raw_dataset, prepare_data, train_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ml_worker")


def main() -> None:
    """Executa a Interface de Linha de Comando (CLI) do ml-worker.

    Suporta os modos de execução:
    - train: Treinamento completo e opcional publicação no Hugging Face Hub.
    - evaluate: Avaliação de desempenho por Validação Cruzada Aninhada (Nested CV).
    - optimize: Otimização de hiperparâmetros com Optuna no dataset completo.
    """
    parser = argparse.ArgumentParser(
        description="ML Worker - Treinamento e Avaliação do Modelo de Imóveis"
    )
    parser.add_argument(
        "--mode",
        choices=["train", "evaluate", "optimize"],
        default="train",
        help="Modo de execução (train, evaluate ou optimize).",
    )
    parser.add_argument(
        "--dataset-source",
        type=str,
        default="meu-ape/imoveis-goiania",
        help="Nome do dataset no HF Hub ou caminho para arquivo Parquet/CSV local.",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=20,
        help="Número de trials para o Optuna.",
    )
    parser.add_argument(
        "--k-folds",
        type=int,
        default=5,
        help="Número de folds para Validação Cruzada.",
    )
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Se informado, envia o modelo e métricas para o Hugging Face Hub.",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default=None,
        help="ID do repositório no HF Hub para envio do modelo (ex: 'usuario/meu-ape-model').",
    )

    args = parser.parse_args()

    if args.mode == "train":
        logger.info("Modo TREINAMENTO selecionado.")
        train_model(
            dataset_source=args.dataset_source,
            repo_id=args.repo_id,
            push_to_hub=args.push_to_hub,
            n_trials=args.n_trials,
            k_folds=args.k_folds,
        )

    elif args.mode == "evaluate":
        logger.info("Modo AVALIAÇÃO (Nested CV) selecionado.")
        df_raw = load_raw_dataset(args.dataset_source)
        X, y = prepare_data(df_raw)
        feature_groups = get_feature_groups(X)
        results = run_nested_cv(
            X=X,
            y=y,
            k_outer=args.k_folds,
            k_inner=args.k_folds,
            n_trials=args.n_trials,
            feature_groups=feature_groups,
        )
        logger.info(f"Resultados da Avaliação: {results['metrics_summary']}")

    elif args.mode == "optimize":
        logger.info("Modo OTIMIZAÇÃO selecionado.")
        df_raw = load_raw_dataset(args.dataset_source)
        X, y = prepare_data(df_raw)
        feature_groups = get_feature_groups(X)
        best_params, best_score = optimize_hyperparameters(
            X=X,
            y=y,
            n_trials=args.n_trials,
            k_folds=args.k_folds,
            feature_groups=feature_groups,
        )
        logger.info(f"Otimização concluída. Melhor RMSE: {best_score:.4f}")
        logger.info(f"Melhores parâmetros: {best_params}")


if __name__ == "__main__":
    main()
