# ✨ Céleste — Observatoire Astronomique

> Application de bureau pour le calcul et la visualisation des positions du Soleil et de la Lune, basée sur les algorithmes de Jean Meeus.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)
![Matplotlib](https://img.shields.io/badge/Graphiques-Matplotlib-orange)
![Licence](https://img.shields.io/badge/Licence-MIT-green)
![CI](https://github.com/Greg50100/Celeste_App/actions/workflows/ci.yml/badge.svg)

---

## Aperçu

Céleste calcule en temps réel — ou pour n'importe quelle date — les positions astronomiques du Soleil et de la Lune, les heures de lever/coucher, les crépuscules et les phases lunaires. Les résultats sont affichés dans une interface sombre moderne accompagnée de deux graphiques interactifs.

**Fonctionnalités principales :**

- **Positions instantanées** : Ascension Droite, Déclinaison, Altitude, Azimut
- **Événements journaliers** : lever, coucher, culmination, aube et crépuscule civils (-6°)
- **Phase lunaire** : illumination en %, nom et emoji de la phase
- **Mode temps réel** : mise à jour automatique toutes les 2 secondes
- **Géolocalisation automatique** : détection de la position via ip-api.com
- **Graphique de trajectoire 24h** : courbes d'altitude avec tooltip interactif
- **Carte du ciel polaire** : projection azimutale avec orientation Nord/Sud/Est/Ouest

---

## Installation

### Prérequis

- Python 3.10 ou supérieur
- pip

### Cloner le dépôt

```bash
git clone https://github.com/Greg50100/Celeste_App.git
cd Celeste_App
```

### Installer les dépendances

```bash
pip install -r requirements.txt
```

### Lancer l'application

```bash
python main.py
```

---

## Utilisation

| Champ | Description |
|-------|-------------|
| **Date & Heure** | Format `JJ/MM/AAAA HH:MM:SS` en Temps Universel (UT) |
| **Latitude** | Degrés décimaux, positif = Nord (ex. `48.85` pour Paris) |
| **Longitude** | Degrés décimaux, positif = Est (ex. `2.35` pour Paris) |

**Boutons :**

- `GÉOLOC` — Remplit automatiquement la latitude et la longitude via votre adresse IP
- `⏱️ TEMPS RÉEL` — Active la mise à jour automatique avec l'heure courante
- `LANCER LE CALCUL` — Lance les calculs pour la date et les coordonnées saisies

**Graphiques :**

- Survolez la courbe 24h pour afficher l'altitude exacte à une heure donnée
- La carte polaire place le Zénith au centre et l'horizon en périphérie

---

## Architecture

Le projet suit le patron **MVC (Modèle-Vue-Contrôleur)** :

```
Celeste_App/
├── main.py                  # Point d'entrée — initialise la fenêtre CTk
├── engine.py                # Modèle — calculs astronomiques purs (MeeusEngine)
├── gui.py                   # Vue + Contrôleur — interface et logique applicative
├── utils.py                 # Utilitaires — formatage HMS, DMS, phases lunaires
├── config.py                # Configuration — palette de couleurs (thème Catppuccin)
├── favorites.json           # Lieux favoris pré-enregistrés (37 villes)
├── requirements.txt         # Dépendances d'exécution
├── requirements-dev.txt     # Dépendances de développement (pytest)
└── tests/
    └── test_engine.py       # 32 tests unitaires pytest (MeeusEngine)
```

### Modèle : `MeeusEngine`

Moteur de calcul entièrement découplé de l'interface. Toutes les méthodes sont
des méthodes de classe ou statiques — aucun état interne n'est conservé.

| Méthode | Rôle |
|---------|------|
| `jour_julien(dte)` | Calcule le Jour Julien (JD) |
| `siecle_julien2000(dte)` | Calcule T en siècles depuis J2000.0 |
| `position_soleil(t)` | Longitude écliptique + distance du Soleil |
| `position_lune(t)` | Longitude, latitude écliptique et parallaxe de la Lune |
| `ecliptique_vers_equatorial(l, b, t)` | Conversion écliptique → équatorial (RA, Dec) |
| `equatorial_vers_horizontal(jd, lat, lon, ra, dec)` | Conversion équatorial → horizontal (Alt, Az) |
| `correction_elevation(h, p)` | Réfraction atmosphérique + parallaxe |
| `trouver_evenements(dte, lat, lon, astre)` | Détection lever/coucher/culmination/crépuscules |

### Optimisation du cache

Le calcul des événements journaliers (1440 itérations × 2 astres) est coûteux.
Un cache basé sur la clé `AAAA-MM-JJ_lat_lon` évite tout recalcul tant que la
date et les coordonnées ne changent pas — notamment utile en mode temps réel.

---

## Références scientifiques

- **Jean Meeus**, *Astronomical Algorithms*, 2e édition, Willmann-Bell, 1998.
  - Chapitre 7 : Jour Julien
  - Chapitre 13 : Transformations de coordonnées
  - Chapitre 16 : Réfraction atmosphérique (formule de Bennett)
  - Chapitre 25 : Position du Soleil (série de faible précision, ±0.01°)
  - Chapitre 47 : Position de la Lune (série simplifiée, ±1°)

---

## Dépendances

| Package | Version minimale | Rôle |
|---------|-----------------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.2 | Interface graphique moderne (dark mode) |
| [matplotlib](https://matplotlib.org/) | 3.10.8 | Graphiques astronomiques interactifs |

`tkinter` et `urllib` font partie de la bibliothèque standard Python.

---

## Feuille de route

### Données & Calculs

- [x] Crépuscules nautique (-12°) et astronomique (-18°)
- [ ] **Système Solaire** — positions de Vénus, Mars, Jupiter, Saturne + orrery 2D
- [ ] **Éclipses** — détection et affichage des éclipses solaires/lunaires à venir
- [ ] **Conjonctions & oppositions** — dates des événements remarquables planétaires
- [ ] **Précision accrue Lune** — passer de la série simplifiée (~1°) à la série complète de Meeus (~0.01°)
- [ ] **Équation du temps** — décalage entre temps solaire vrai et temps solaire moyen

### Interface & Visualisation

- [ ] **Couleurs de crépuscule** — fond du graphique Trajectoires coloré selon les phases du jour réelles
- [ ] **Carte du ciel interactive** — clic sur une étoile/planète pour afficher sa fiche
- [ ] **Carte polaire améliorée** — constellations et quadrillage de magnitude
- [ ] **Thème clair** — bascule entre Catppuccin Mocha (sombre) et thème clair

### Expérience utilisateur

- [x] Lieux favoris — sauvegarde/chargement de positions nommées (`favorites.json`)
- [x] Conversion fuseau horaire (UT → heure locale via sélecteur UTC±N)
- [x] Étoiles principales sur la carte du ciel (32 étoiles, taille proportionnelle à la magnitude)
- [ ] **Historique de calcul** — liste des derniers calculs rechargeable en un clic
- [ ] **Export des données** — éphémérides du jour en CSV ou PDF
- [ ] **Recherche de lieu** — geocoding par nom de ville
- [ ] **Calendrier lunaire mensuel** — vue mois avec phase de chaque jour

### Technique & Qualité

- [ ] **Tests unitaires** — pytest sur `engine.py` et `utils.py`, valeurs de référence Meeus
- [ ] **Packaging exécutable** — build PyInstaller `.exe` (Windows) / `.app` (macOS)
- [ ] **Multilingue** — interface EN/FR switchable (i18n)

---

## Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour les détails.
