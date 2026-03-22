"""
constellations.py — Star Constellation Data for Sky Map
========================================================
Additional stars, constellation edges, and reverse lookup.
"""

# Additional stars: {name: (RA hours, Dec degrees, magnitude)}
STARS_EXTRA = {
    # Orion
    "Mintaka":   ( 5.5335,  -0.2991, 2.23),
    "Saiph":     ( 5.7954,  -9.6697, 2.07),
    # Big Dipper (Ursa Major)
    "Mizar":     (13.3988,  54.9254, 2.23),
    "Megrez":    (12.2571,  57.0326, 3.31),
    # Cassiopeia
    "Schedar":   ( 0.6751,  56.5372, 2.24),
    "Caph":      ( 0.1530,  59.1498, 2.28),
    "Navi":      ( 0.9451,  60.7167, 2.47),
    "Ruchbah":   ( 1.4301,  60.2353, 2.68),
    "Segin":     ( 1.9068,  63.6700, 3.37),
    # Little Dipper (Ursa Minor)
    "Kochab":    (14.8451,  74.1555, 2.07),
    # Scorpius
    "Shaula":    (17.5603, -37.1038, 1.62),
    "Dschubba":  (16.0055, -22.6217, 2.29),
    "Sargas":    (17.6217, -42.9978, 1.87),
}

# Constellations: {name: list of (star_a, star_b)}
# Star names must match keys in _STARS (accents included).
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
    "Ursa Major": [
        ("Dubhe", "Merak"),
        ("Merak", "Phecda"),
        ("Phecda", "Megrez"),
        ("Megrez", "Alioth"),
        ("Alioth", "Mizar"),
        ("Mizar", "Alkaid"),
    ],
    "Cassiopeia": [
        ("Caph", "Schedar"),
        ("Schedar", "Navi"),
        ("Navi", "Ruchbah"),
        ("Ruchbah", "Segin"),
    ],
    "Gemini": [
        ("Castor", "Pollux"),
        ("Pollux", "Alhena"),
    ],
    "Leo": [
        ("Regulus", "Denebola"),
    ],
    "Scorpius": [
        ("Dschubba", "Antares"),
        ("Antares", "Shaula"),
        ("Antares", "Sargas"),
    ],
    "Summer Triangle": [
        ("Vega", "Deneb"),
        ("Deneb", "Altair"),
        ("Altair", "Vega"),
    ],
    "Ursa Minor": [
        ("Polaris", "Kochab"),
    ],
}

# Reverse lookup: star name → list of constellations
STAR_CONSTELLATION = {}
for _const_name, _edges in CONSTELLATIONS.items():
    for _a, _b in _edges:
        STAR_CONSTELLATION.setdefault(_a, []).append(_const_name)
        STAR_CONSTELLATION.setdefault(_b, []).append(_const_name)
# Deduplicate
for _k in STAR_CONSTELLATION:
    STAR_CONSTELLATION[_k] = list(dict.fromkeys(STAR_CONSTELLATION[_k]))
