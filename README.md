# ✨ Céleste — observatoire astronomique

> Application de bureau qui calcule et affiche la position du Soleil, de la Lune et des planètes, d'après les algorithmes de Jean Meeus.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)
![Matplotlib](https://img.shields.io/badge/Graphiques-Matplotlib-orange)
![Licence](https://img.shields.io/badge/Licence-MIT-green)
![CI](https://github.com/Greg50100/Celeste_App/actions/workflows/ci.yml/badge.svg)

**Projet actif** · fait partie de la famille Ganymede : [site web](https://greg50100.github.io/personnal-site/) ·
[application Android](https://github.com/Greg50100/Ganymede) · [Céleste pour Home Assistant](https://github.com/Greg50100/Celeste_HA)

---

## Présentation

Céleste calcule en temps réel — ou pour n'importe quelle date — la position du Soleil, de la Lune et de quatre planètes
(Vénus, Mars, Jupiter, Saturne), les événements du jour (lever, coucher, crépuscules), les phases de la Lune, les éclipses,
les conjonctions et les oppositions. Les résultats s'affichent dans une interface sombre avec des graphiques interactifs et
une carte du ciel.

**Fonctionnalités principales :**

- **Positions instantanées** — ascension droite, déclinaison, hauteur, azimut
- **Événements du jour** — lever, coucher, culmination ; crépuscules civil (−6°), nautique (−12°) et astronomique (−18°)
- **Phase de la Lune** — pourcentage éclairé, nom de la phase et émoji
- **Mode temps réel** — mise à jour automatique toutes les 2 s (réglable)
- **Géolocalisation automatique** — détection de la position via ip-api.com
- **Trajectoire sur 24 h** — courbes de hauteur avec info-bulle interactive
- **Carte du ciel polaire** — projection azimutale orientée N/S/E/O, plus de 32 étoiles nommées, constellations, planètes
- **Onglet système solaire** — positions de Vénus, Mars, Jupiter et Saturne
- **Prévision des éclipses** — type (totale, annulaire, hybride), rapport des diamètres, magnitude, durée de la phase centrale
- **Conjonctions et oppositions** — prochains événements planétaires
- **Équation du temps** — écart entre temps solaire vrai et temps solaire moyen
- **Favoris** — enregistrement des lieux (37 villes préchargées)
- **Fuseaux horaires** — conversion TU → heure locale par sélecteur UTC±N
- **Export PDF** — éphémérides du jour
- **Interface multilingue** — français, anglais, espagnol, allemand (`--lang` ou réglages)
- **Réglages persistants** — thème, langue, lieu par défaut, unités, intervalle temps réel (`settings.json`)

---

## Installation

Prérequis : Python 3.10 ou plus récent, et pip.

```bash
git clone https://github.com/Greg50100/Celeste_App.git
cd Celeste_App
pip install -r requirements.txt
python main.py
```

Choix de la langue :

```bash
python main.py --lang fr   # français
python main.py --lang en   # anglais (par défaut)
python main.py --lang es   # espagnol
python main.py --lang de   # allemand
```

---

## Utilisation

| Champ | Description |
|-------|-------------|
| **Date et heure** | Format `JJ/MM/AAAA HH:MM:SS`, en temps universel (TU) |
| **Latitude** | Degrés décimaux, positif = nord (ex. `48.85` pour Paris) |
| **Longitude** | Degrés décimaux, positif = est (ex. `2.35` pour Paris) |

**Boutons :**

- `GEOLOC` — remplit la latitude et la longitude à partir de l'adresse IP
- `⏱ LIVE` — active le mode temps réel (intervalle réglable)
- `CALCULATE` — lance les calculs pour la date et le lieu saisis
- `🖨 EXPORT PDF` — exporte les éphémérides du jour en PDF

**Graphiques :**

- Survolez la courbe sur 24 h pour lire la hauteur exacte à toute heure
- La carte polaire place le zénith au centre et l'horizon au bord
- Cliquez sur une planète de la carte du ciel pour afficher sa fiche

---

## Architecture

Le projet suit le modèle **MVC (modèle-vue-contrôleur)** :

```
Celeste_App/
├── main.py              # Point d'entrée — initialisation i18n, fenêtre CTk
├── engine.py            # Modèle — calculs astronomiques purs (MeeusEngine)
├── gui.py               # Vue + contrôleur — interface et logique applicative
├── utils.py             # Utilitaires — formats HMS/DMS, noms des phases
├── config.py            # Configuration — palette (thème Catppuccin Mocha)
├── i18n.py              # Internationalisation — traductions par clé avec repli
├── settings.py          # Préférences persistantes (settings.json)
├── constellations.py    # Catalogue d'étoiles et tracés des constellations
├── export_pdf.py        # Export PDF des éphémérides
├── favorites.json       # Lieux préchargés (37 villes)
├── settings.json        # Préférences (générées automatiquement)
├── locales/             # Traductions (fr.json est la référence)
├── scripts/             # Scripts annexes (fiche haute précision Skyfield/INPOP)
├── requirements.txt     # Dépendances d'exécution
├── requirements-dev.txt # Dépendances de développement (pytest)
└── tests/               # Tests unitaires (moteur, i18n, utilitaires)
```

### Modèle : `MeeusEngine`

Moteur de calcul entièrement découplé : uniquement des méthodes de classe ou statiques, sans état interne.

| Méthode | Rôle |
|---------|------|
| `julian_day(dte)` | Jour julien (JJ) |
| `julian_century_j2000(dte)` | T en siècles juliens depuis J2000,0 |
| `sun_position(t)` | Longitude écliptique et distance du Soleil — série courte (~0,01°) |
| `sun_position_hp(t)` | Position du Soleil — VSOP87 tronquée (~1″) |
| `moon_position(t)` | Longitude, latitude et parallaxe de la Lune — série de base (Meeus ch. 47) |
| `moon_position_elp2000(t)` | Position de la Lune — séries ELP2000-82B étendues (~10″) |
| `ecliptic_to_equatorial(l, b, t)` | Écliptique → équatorial (AD, Déc) |
| `equatorial_to_horizontal(jd, lat, lon, ra, dec)` | Équatorial → horizontal (hauteur, azimut) |
| `elevation_correction(h, p)` | Réfraction atmosphérique et parallaxe |
| `find_events(dte, lat, lon, body)` | Lever, coucher, culmination, crépuscules |
| `planet_position(name, t)` | Position héliocentrique → géocentrique (Vénus, Mars, Jupiter, Saturne) |
| `equation_of_time(t)` | Équation du temps en minutes |
| `angular_separation(ra1, dec1, ra2, dec2)` | Séparation angulaire entre deux astres |
| `find_conjunctions(year, body1, body2)` | Prochaines conjonctions et oppositions |
| `find_eclipses(year)` | Éclipses de Soleil, avec type et magnitude |

### Cache

Le calcul des événements du jour (1 440 itérations × 2 astres) est coûteux. Un cache indexé par `AAAA-MM-JJ_lat_lon`
évite de le refaire tant que la date et le lieu ne changent pas, ce qui est précieux en mode temps réel.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

| Fichier | Portée |
|---------|--------|
| `test_engine.py` | Jour julien, positions Soleil/Lune, changements de repère, événements, planètes |
| `test_engine_hp.py` | Soleil VSOP87, Lune ELP2000, équation du temps, séparations, conjonctions, éclipses |
| `test_i18n.py` | Chargement des traductions, repli, changement de langue |
| `test_utils.py` | Formats HMS/DMS (retenues), noms et normalisation des phases |

---

## Références scientifiques

- **Jean Meeus**, *Astronomical Algorithms*, 2e édition, Willmann-Bell, 1998.
  - Chapitre 7 — Jour julien
  - Chapitre 13 — Changements de coordonnées
  - Chapitre 16 — Réfraction atmosphérique (formule de Bennett)
  - Chapitre 25 — Position du Soleil (série courte, ±0,01°)
  - Chapitre 28 — Équation du temps
  - Chapitre 32 — Position du Soleil VSOP87 (~1″)
  - Chapitre 47 — Position de la Lune (série de base ±0,01° + ELP2000-82B ±10″)
  - Chapitre 54 — Prévision des éclipses de Soleil

---

## Dépendances

| Paquet | Version min. | Rôle |
|--------|-------------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.2 | Interface graphique sombre moderne |
| [matplotlib](https://matplotlib.org/) | 3.10.8 | Graphiques astronomiques interactifs |
| [reportlab](https://www.reportlab.com/) | 4.0 | Export PDF |

`tkinter`, `urllib` et `json` font partie de la bibliothèque standard de Python.

---

## Feuille de route

### Données et calculs

- [x] Crépuscules nautique (−12°) et astronomique (−18°)
- [x] **Système solaire** — positions de Vénus, Mars, Jupiter et Saturne
- [x] **Éclipses de Soleil** — type, magnitude, durée de la phase centrale
- [x] **Conjonctions et oppositions** — prochains événements planétaires
- [x] **Précision de la Lune** — séries ELP2000-82B étendues (~10″)
- [x] **Équation du temps**
- [ ] **Planétaire 2D** — orbites animées
- [ ] **Éclipses de Lune** — étendre la détection à la Lune

### Interface et visualisation

- [x] Étoiles principales sur la carte (32+, taille selon la magnitude)
- [x] Tracés des constellations sur la carte polaire
- [x] Planètes sur la carte du ciel (info-bulle et fiche au clic)
- [ ] **Couleurs des crépuscules** — fond du graphique de trajectoire coloré selon le moment de la journée
- [ ] **Carte du ciel interactive** — fiche complète d'une étoile au clic
- [ ] **Thème clair** — bascule entre Catppuccin Mocha (sombre) et Latte (clair)

### Confort d'utilisation

- [x] Favoris — enregistrement des lieux (`favorites.json`)
- [x] Fuseaux horaires (TU → heure locale par sélecteur UTC±N)
- [x] **Export** — éphémérides du jour en PDF
- [x] **Interface multilingue** — FR / EN / ES / DE
- [x] **Réglages persistants** — langue, thème, lieu, intervalle temps réel (`settings.json`)
- [ ] **Historique des calculs** — derniers calculs rechargeables en un clic
- [ ] **Recherche de lieu** — géocodage par nom de ville
- [ ] **Calendrier lunaire mensuel** — vue du mois avec la phase de chaque jour

### Technique et qualité

- [x] **Tests unitaires** — pytest sur `engine.py`, `utils.py` et `i18n.py` (4 fichiers, ~90 cas)
- [ ] **Exécutable** — PyInstaller `.exe` (Windows) / `.app` (macOS)

---

## Licence

Projet distribué sous licence MIT : voir le fichier `LICENSE`.
