from typing import Dict


BINS_INFO: list[tuple[str, list[float], list[str]]] = [
    (
        "area_m2",
        [0, 20, 50, 90, 150, float("inf")],
        ["muito_pequeno", "pequeno", "medio", "grande", "muito_grande"]
    ),
    (
        "condominio",
        [0, 300, 1000, float("inf")],
        ["baixo", "medio", "alto"]
    ),
]

POINTS: Dict[str, tuple[float, float]]= {
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

PAIRS: list[tuple[str, str]] = [
    ("area_m2", "banheiros"),
    ("area_m2", "quartos"),
    ("banheiros", "quartos"),
    ("quartos", "vagas"),
]