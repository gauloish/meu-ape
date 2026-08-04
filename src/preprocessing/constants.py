from typing import List, Dict


# ----- Unused Features -----
UNUSED_FEATURES: List[str] = [
    "id",
    "url",
    "moeda",
    "cidade",
    "estado",
    "pais",
    "fotos_urls",
    "descricao_completa",
]

# ===== Water / Pool =====

POOL_AMENITIES: List[str] = [
    "Pool",
    "Adult Pool",
    "Childrens Pool",
    "Heated Pool",
    "Private Pool",
    "Covered Pool",
    "Semi Olympic Pool",
    "Reflecting Pool",
    "Pool Bar",
]

# ===== Gourmet =====

GOURMET_AMENITIES: List[str] = [
    "Barbecue Grill",
    "Barbecue Balcony",
    "Pizza Oven",
    "Gourmet Space",
    "Gourmet Balcony",
    "Gourmet Kitchen",
]

# ==== Health & Wellness =====

FITNESS_AMENITIES: List[str] = [
    "Gym",
    "Fitness Room",
]

WELLNESS_AMENITIES: List[str] = [
    "Sauna",
    "Spa",
    "Whirlpool",
    "Hot Tub",
    "Massage Room",
]

# ===== Social Areas =====

SOCIAL_AMENITIES: List[str] = [
    "Party Hall",
    "Adult Game Room",
    "Games Room",
    "Cinema",
    "Bar",
    "Coffee Shop",
    "Restaurant",
    "Covention Hall",
    "Zen Space",
]

WORK_AMENITIES: List[str] = [
    "Coworking",
    "Meeting Room",
    "Library",
]

KIDS_AMENITIES: List[str] = [
    "Playground",
    "Toys Place",
    "Sand Pit",
    "Teen Space",
]

# ===== Sports ======

SPORTS_AMENITIES: List[str] = [
    "Sports Court",
    "Tennis Court",
    "Football Field",
    "Indoor Soccer",
    "Squash",
    "Skate Lane",
    "Hiking Trail",
    "Golf Field",
]

# ===== Security =====

ACCESS_CONTROL_AMENITIES: List[str] = [
    "Gated Community",
    "Concierge 24h",
    "Reception",
]

SECURITY_AMENITIES: List[str] = [
    "Watchman",
    "Patrol",
    "Alarm System",
    "Safety Circuit",
    "Electronic Gate",
    "Intercom",
    "Security Camera",
    "Security Cabin",
    "Armored Security Cabin",
    "Fence",
    "Security 24 Hours",
]

# ===== Mobility =====

GARAGE_AMENITIES: List[str] = [
    "Garage",
    "Parking",
    "Guest Parking",
    "Valet Parking",
    "Bicycles Place",
]

# ===== Accessibility =====

ACCESSIBILITY_AMENITIES: List[str] = [
    "Elevator",
    "Disabled Access",
]

# ===== Pets =====

PET_AMENITIES: List[str] = [
    "Pets Allowed",
    "Pet Space",
]

# ===== Outdoor =====

BALCONY_AMENITIES: List[str] = [
    "Balcony",
    "Wall Balcony",
    "Deck",
]

GREEN_AREA_AMENITIES: List[str] = [
    "Garden",
    "Backyard",
    "Green Space",
    "Grass",
    "Fruit Trees",
    "Pomar",
    "Vegetable Garden",
    "Tree Climbing",
]

VIEW_AMENITIES: List[str] = [
    "Exterior View",
    "Lake",
    "River",
    "Lake View",
    "Mountain View",
    "Sea View",
    "Panoramic View",
]

# ===== Finishes =====

FINISH_AMENITIES: List[str] = [
    "Porcelain",
    "Blindex Box",
    "Sanca",
    "Aluminum Window",
    "Laminated Floor",
    "Wood Floor",
    "Vinyl Floor",
    "Carpet",
    "Drywall",
    "Glass Wall",
    "Thermal Insulation",
    "Cold Floor",
    "Burnt Cement",
    "Platibanda",
]

BUILTIN_FURNITURE_AMENITIES: List[str] = [
    "Planned Furniture",
    "Builtin Wardrobe",
    "Bedroom Wardrobe",
    "Bathroom Cabinets",
    "Kitchen Cabinets",
    "Closet",
    "Dress Room2",
]

LAYOUT_AMENITIES: List[str] = [
    "Lavabo",
    "Reversible Room",
    "Dividers",
    "Integrated Environments",
    "Large Room",
    "Small Room",
    "High Ceiling Height",
]

# ===== Kitchen & Service =====

KITCHEN_AMENITIES: List[str] = [
    "Kitchen",
    "American Kitchen",
    "Large Kitchen",
    "Pantry",
    "Copa",
    "Dinner Room",
    "Lunch Room",
]

SERVICE_AMENITIES: List[str] = [
    "Laundry",
    "Service Area",
    "Service Bathroom",
    "Service Room",
    "Employee Dependency",
    "Service Entrance",
]

# ===== Comfort =====

COMFORT_AMENITIES: List[str] = [
    "Air Conditioning",
    "Heating",
    "Natural Ventilation",
    "Soundproofing",
    "Large Window",
]

FURNISHED_AMENITIES: List[str] = [
    "Furnished",
]

# ===== Technology =====

SMART_HOME_AMENITIES: List[str] = [
    "Smart Apartment",
    "Smart Condominium",
    "Digital Locker",
]

CONNECTIVITY_AMENITIES: List[str] = [
    "Internet Access",
    "Cable Tv",
    "Full Cabling",
]

# ===== Infraestructure =====

ENERGY_AMENITIES: List[str] = [
    "Solar Energy",
    "Electric Generator",
    "Eletric Charger",
]

WATER_INFRASTRUCTURE_AMENITIES: List[str] = [
    "Water Tank",
    "Artesian Well",
    "Well",
]

SUSTAINABILITY_AMENITIES: List[str] = [
    "Eco Garbage Collector",
    "Eco Condominium",
]

# ----- Feature Mappings -----

FEATURES_MAPPING: Dict[str, List[str]] = {
    "piscina": POOL_AMENITIES,
    "espaco_gourmet": GOURMET_AMENITIES,
    "academia": FITNESS_AMENITIES,
    "spa_massagem": WELLNESS_AMENITIES,
    "espaco_lazer": SOCIAL_AMENITIES,
    "area_trabalho": WORK_AMENITIES,
    "espaco_infantil": KIDS_AMENITIES,
    "area_esportiva": SPORTS_AMENITIES,
    "portaria": ACCESS_CONTROL_AMENITIES,
    "seguranca": SECURITY_AMENITIES,
    "servicos_garagem": GARAGE_AMENITIES,
    "acessibilidade": ACCESSIBILITY_AMENITIES,
    "pets": PET_AMENITIES,
    "varanda": BALCONY_AMENITIES,
    "area_verde": GREEN_AREA_AMENITIES,
    "espaco_natural": VIEW_AMENITIES,
    "acabamento_premium": FINISH_AMENITIES,
    "moveis_embutidos": BUILTIN_FURNITURE_AMENITIES,
    "layout_premium": LAYOUT_AMENITIES,
    "cozinha": KITCHEN_AMENITIES,
    "servicos": SERVICE_AMENITIES,
    "conforto_interno": COMFORT_AMENITIES,
    "mobiliado": FURNISHED_AMENITIES,
    "casa_inteligente": SMART_HOME_AMENITIES,
    "servicos_conectividade": CONNECTIVITY_AMENITIES,
    "infra_energetica": ENERGY_AMENITIES,
    "infra_hidrica": WATER_INFRASTRUCTURE_AMENITIES,
    "servicos_sustentaveis": SUSTAINABILITY_AMENITIES,
}