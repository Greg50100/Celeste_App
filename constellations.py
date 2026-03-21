"""
constellations.py — Données des constellations pour la carte du ciel
====================================================================
Étoiles supplémentaires, arêtes de constellations et lookup inverse.
"""

# Étoiles supplémentaires : {nom: (RA heures, Dec degrés, magnitude)}
ETOILES_SUPPLEMENTAIRES = {
    # Orion
    "Mintaka":   ( 5.5335,  -0.2991, 2.23),
    "Saiph":     ( 5.7954,  -9.6697, 2.07),
    # Grande Ourse
    "Mizar":     (13.3988,  54.9254, 2.23),
    "Megrez":    (12.2571,  57.0326, 3.31),
    # Cassiopée
    "Schedar":   ( 0.6751,  56.5372, 2.24),
    "Caph":      ( 0.1530,  59.1498, 2.28),
    "Navi":      ( 0.9451,  60.7167, 2.47),
    "Ruchbah":   ( 1.4301,  60.2353, 2.68),
    "Segin":     ( 1.9068,  63.6700, 3.37),
    # Petite Ourse
    "Kochab":    (14.8451,  74.1555, 2.07),
    # Scorpion
    "Shaula":    (17.5603, -37.1038, 1.62),
    "Dschubba":  (16.0055, -22.6217, 2.29),
    "Sargas":    (17.6217, -42.9978, 1.87),
}

# Constellations : {nom: liste de (étoile_a, étoile_b)}
# Les noms d'étoiles doivent correspondre aux clés de _ETOILES (accents inclus).
CONSTELLATIONS = {
    "Orion": [
        ("Betelgeuse", "Bellatrix"),
        ("Bellatrix", "Mintaka"),
        ("Mintaka", "Alnilam"),
        ("Alnilam", "Alnitak"),
        ("Alnitak", "Saiph"),
        ("Saiph", "Rigel"),
        ("Rigel", "Bellatrix"),
    ],
    "Grande Ourse": [
        ("Dubhe", "Mérak"),
        ("Mérak", "Phécda"),
        ("Phécda", "Megrez"),
        ("Megrez", "Alioth"),
        ("Alioth", "Mizar"),
        ("Mizar", "Alkaid"),
    ],
    "Cassiopée": [
        ("Caph", "Schedar"),
        ("Schedar", "Navi"),
        ("Navi", "Ruchbah"),
        ("Ruchbah", "Segin"),
    ],
    "Gémeaux": [
        ("Castor", "Pollux"),
        ("Pollux", "Alhéna"),
    ],
    "Lion": [
        ("Régulus", "Denébola"),
    ],
    "Scorpion": [
        ("Dschubba", "Antarès"),
        ("Antarès", "Shaula"),
        ("Antarès", "Sargas"),
    ],
    "Triangle d'été": [
        ("Véga", "Deneb"),
        ("Deneb", "Altaïr"),
        ("Altaïr", "Véga"),
    ],
    "Petite Ourse": [
        ("Polaris", "Kochab"),
    ],
}

# Lookup inverse : nom d'étoile → liste de constellations
ETOILE_CONSTELLATION = {}
for _nom_const, _aretes in CONSTELLATIONS.items():
    for _a, _b in _aretes:
        ETOILE_CONSTELLATION.setdefault(_a, []).append(_nom_const)
        ETOILE_CONSTELLATION.setdefault(_b, []).append(_nom_const)
# Dédupliquer
for _k in ETOILE_CONSTELLATION:
    ETOILE_CONSTELLATION[_k] = list(dict.fromkeys(ETOILE_CONSTELLATION[_k]))
