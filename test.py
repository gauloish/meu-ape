from ml_core.preprocessing.data_cleaning import DataCleaner
from ml_core.preprocessing.feature_extraction import FeatureExtractor
from ml_core.preprocessing.geocoding_enrichment import GeocodingEnricher

from ml_core.transformers.geodesic_distance_transformer import GeodesicDistanceTransformer

from sklearn.pipeline import Pipeline

from logging_settings import setup_logger
import pandas as pd

from dotenv import (
    load_dotenv,
    find_dotenv,
)

load_dotenv(find_dotenv())

logger = setup_logger(__name__)

points = {
    # Parques
    "lago_das_rosas": (-16.6800351, -49.2739961),
    "vaca_brava": (-16.7096266, -49.2731507),
    "parque_areiao": (-16.7072239, -49.2591976),
    "parque_flamboyant": (-16.7071325, -49.2978223),
    "bosque_dos_buritis": (-16.6820805, -49.2800136),

    # Shoppings
    "flamboyant_shopping": (-16.7103239, -49.2372795),
    "goiania_shopping": (-16.7079145, -49.2722946),
    "passeio_das_aguas": (-16.6301889,-49.276212),
    "shopping_cerrado": (-16.6659975, -49.3045483),
    "buriti_shopping": (-16.7414558, -49.2772061),

    # Hospitais
    "hospital_albert_einstein": (-16.6964791, -49.2696419),
    "hospital_mater_dei": (-16.7194404, -49.2664608),
    "hospital_anis_rassi": (-16.6787898, -49.2691866),
    "hospital_jacob_facuri": (-16.6732056, -49.259802),
    "hugol": (-16.6494872, -49.3465465),
    "crer": (-16.6549245, -49.2471117),
    "hgg": (-16.6792106, -49.2709921),

    # Universidades
    "ufg_samambaia": (-16.6062069, -49.2614624),
    "ufg_universitario": (-16.6752787, -49.2460934),
    "puc": (-16.6777968, -49.2467693),
    "ifg": (-16.666101, -49.2558974),

    # Setores
    "setor_central": (-16.6717385, -49.2678839),
    "setor_bueno": (-16.7002167, -49.2845502),
    "setor_marista": (-16.7012624, -49.2821738),
    "jardim_goias": (-16.6983463, -49.2481699),

    # Rodoviária e Aeroporto
    "aeroporto": (-16.6288656,-49.2569422),
    "rodoviaria": (-16.6597328,-49.2608247),
}
import sklearn
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s")

    data_cleaner = DataCleaner()
    feature_extractor = FeatureExtractor()
    geocoding_enricher = GeocodingEnricher()

    df = pd.read_csv("data/raw/zap_dataset.csv").iloc[:100]

    df = (df
        .pipe(data_cleaner)
        .pipe(feature_extractor)
        .pipe(geocoding_enricher)
    )

    geodesic_features = GeodesicDistanceTransformer(
        points=points
    )

    pipeline = Pipeline(steps=[
        ("geodesic_features", geodesic_features)
    ])

    X = df.drop("preco", axis="columns")
    y = df["preco"]

    print(X[["latitude", "longitude"]].head())

    logger.info("Finalizing all.")
