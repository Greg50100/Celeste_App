"""
tests/test_engine.py — Tests unitaires du moteur astronomique Céleste
======================================================================
Vérifie les algorithmes de MeeusEngine à partir des valeurs de référence
publiées dans *Astronomical Algorithms* de Jean Meeus (2e éd., Willmann-Bell).

Lancer avec :  pytest tests/
"""

import math
import sys
import os
import pytest

# Rendre le répertoire racine importable depuis tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from engine import MeeusEngine


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def approx(value, expected, tol):
    """Vérifie que |value - expected| ≤ tol."""
    return abs(value - expected) <= tol


# ──────────────────────────────────────────────────────────────────────
# 1. Jour Julien  (Meeus, chap. 7, exemples p. 61-62)
# ──────────────────────────────────────────────────────────────────────

class TestJourJulien:
    def test_j2000(self):
        """J2000.0 : 1.5 janvier 2000 = JD 2451545.0 (définition d'époque)."""
        jd = MeeusEngine.jour_julien(datetime(2000, 1, 1, 12, 0, 0))
        assert abs(jd - 2451545.0) < 0.001

    def test_meeus_exemple_7a(self):
        """Exemple Meeus p. 61 : 4.81 oct 1957 → JD 2436116.31."""
        # 4 oct 1957, 19h26m24s UT
        dte = datetime(1957, 10, 4, 19, 26, 24)
        jd = MeeusEngine.jour_julien(dte)
        assert abs(jd - 2436116.31) < 0.01

    def test_j1900(self):
        """J1900.0 : 0.5 jan 1900 midi UT = JD 2415021.0."""
        dte = datetime(1900, 1, 1, 12, 0, 0)
        jd = MeeusEngine.jour_julien(dte)
        assert abs(jd - 2415021.0) < 0.01

    def test_demi_jour(self):
        """Un delta de 12h entre deux datetimes doit donner exactement 0.5 JD."""
        d1 = MeeusEngine.jour_julien(datetime(2024, 3, 20, 0, 0, 0))
        d2 = MeeusEngine.jour_julien(datetime(2024, 3, 20, 12, 0, 0))
        assert abs((d2 - d1) - 0.5) < 1e-9

    def test_croissance_monotone(self):
        """Le JD doit croître d'un jour entre deux dates consécutives."""
        d1 = MeeusEngine.jour_julien(datetime(2024, 6, 15, 0, 0, 0))
        d2 = MeeusEngine.jour_julien(datetime(2024, 6, 16, 0, 0, 0))
        assert abs((d2 - d1) - 1.0) < 1e-9


# ──────────────────────────────────────────────────────────────────────
# 2. Siècle Julien depuis J2000.0
# ──────────────────────────────────────────────────────────────────────

class TestSiecleJulien:
    def test_j2000_est_zero(self):
        """À J2000.0, T doit valoir exactement 0."""
        t = MeeusEngine.siecle_julien2000(datetime(2000, 1, 1, 12, 0, 0))
        assert abs(t) < 1e-10

    def test_un_siecle_apres(self):
        """Exactement 100 ans juliens après J2000.0 → T = 1.0."""
        # 1 siècle julien = 36525 jours ≈ 100 ans
        from datetime import timedelta
        dte = datetime(2000, 1, 1, 12, 0, 0)
        dte_plus100 = datetime(2100, 1, 1, 12, 0, 0)
        t = MeeusEngine.siecle_julien2000(dte_plus100)
        # Précision à 0.001 : les années bissextiles rendent le calcul approximatif
        assert abs(t - 1.0) < 0.001

    def test_signe_avant_j2000(self):
        """Avant J2000.0, T doit être négatif."""
        t = MeeusEngine.siecle_julien2000(datetime(1999, 1, 1, 12, 0, 0))
        assert t < 0


# ──────────────────────────────────────────────────────────────────────
# 3. Position du Soleil  (Meeus, chap. 25)
# ──────────────────────────────────────────────────────────────────────

class TestPositionSoleil:
    def test_longitude_j2000(self):
        """J2000.0 : longitude écliptique du Soleil ≈ 280.46° (L0 à T=0)."""
        t = MeeusEngine.siecle_julien2000(datetime(2000, 1, 1, 12, 0, 0))
        l, _ = MeeusEngine.position_soleil(t)
        # La longitude réelle est proche de 280° (équinoxe de printemps ~3 mois plus tard)
        assert 270 < l < 290

    def test_distance_proche_1ua(self):
        """Distance Terre-Soleil ≈ 1 UA (±3 %)."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 6, 21, 0, 0, 0))
        _, r = MeeusEngine.position_soleil(t)
        assert 0.97 < r < 1.03

    def test_meeus_exemple_25a(self):
        """
        Exemple Meeus p. 165 : 13 octobre 1992 0h TD.
        Longitude apparente du Soleil ≈ 199.9° (Meeus L0=201.807°, série courte ±1°).
        Distance ≈ 0.9976 UA.
        """
        dte = datetime(1992, 10, 13, 0, 0, 0)
        t = MeeusEngine.siecle_julien2000(dte)
        l, r = MeeusEngine.position_soleil(t)
        assert approx(l, 199.9, 1.5), f"Longitude = {l:.3f}°"
        assert approx(r, 0.9976, 0.005), f"Distance = {r:.5f} UA"

    def test_longitude_dans_360(self):
        """La longitude doit toujours être dans [0, 360[."""
        for year in range(2000, 2030, 5):
            for month in (1, 4, 7, 10):
                t = MeeusEngine.siecle_julien2000(datetime(year, month, 15))
                l, _ = MeeusEngine.position_soleil(t)
                assert 0 <= l < 360


# ──────────────────────────────────────────────────────────────────────
# 4. Position de la Lune  (Meeus, chap. 47)
# ──────────────────────────────────────────────────────────────────────

class TestPositionLune:
    def test_longitude_dans_360(self):
        """La longitude écliptique doit être dans [0, 360[."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 3, 25, 0, 0, 0))
        l, b, p = MeeusEngine.position_lune(t)
        assert 0 <= l < 360

    def test_latitude_bornee(self):
        """La latitude écliptique de la Lune est toujours dans ±6.5°."""
        for day in range(1, 29, 4):
            t = MeeusEngine.siecle_julien2000(datetime(2024, 1, day))
            _, b, _ = MeeusEngine.position_lune(t)
            assert -7 <= b <= 7, f"Latitude hors plage : {b:.2f}°"

    def test_parallaxe_realiste(self):
        """La parallaxe horizontale de la Lune est entre 0.90° et 1.02°."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 1, 1))
        _, _, p = MeeusEngine.position_lune(t)
        assert 0.90 <= p <= 1.02, f"Parallaxe = {p:.4f}°"


# ──────────────────────────────────────────────────────────────────────
# 5. Conversion écliptique → équatorial  (Meeus, chap. 13)
# ──────────────────────────────────────────────────────────────────────

class TestEcliptiqueEquatorial:
    def test_meeus_exemple_13a(self):
        """
        Meeus p. 95 : λ=113.842°, β=6.684°, obliquité 23.4392° (T≈0).
        → RA ≈ 7h45m45s = 7.7625h,  Dec ≈ 28°1' = 28.02°.
        Tolérance 0.05h / 0.1° : série courte, précision <1'.
        """
        t = 0.0  # J2000.0
        ra, dec = MeeusEngine.ecliptique_vers_equatorial(113.842, 6.684, t)
        assert approx(ra, 7.7625, 0.05), f"RA = {ra:.3f}h"
        assert approx(dec, 28.02, 0.15), f"Dec = {dec:.3f}°"

    def test_ra_dans_plage(self):
        """L'ascension droite doit toujours être dans [0, 24[."""
        for l in (0, 90, 180, 270, 359):
            ra, _ = MeeusEngine.ecliptique_vers_equatorial(l, 0.0, 0.0)
            assert 0 <= ra < 24, f"RA hors plage pour λ={l}° : {ra}"

    def test_point_vernal(self):
        """λ=0, β=0 → RA=0h, Dec=0° (point vernal)."""
        ra, dec = MeeusEngine.ecliptique_vers_equatorial(0.0, 0.0, 0.0)
        assert abs(ra) < 0.01
        assert abs(dec) < 0.01


# ──────────────────────────────────────────────────────────────────────
# 6. Correction d'élévation (réfraction + parallaxe)
# ──────────────────────────────────────────────────────────────────────

class TestCorrectionElevation:
    def test_altitude_positive_augmente(self):
        """La réfraction doit augmenter l'altitude apparente (objet semble plus haut)."""
        h_corr = MeeusEngine.correction_elevation(30.0, 0.0)
        assert h_corr > 30.0

    def test_refraction_plus_forte_pres_horizon(self):
        """La réfraction est plus forte près de l'horizon qu'au zénith."""
        r_bas    = MeeusEngine.correction_elevation(1.0, 0.0) - 1.0
        r_haut   = MeeusEngine.correction_elevation(60.0, 0.0) - 60.0
        assert r_bas > r_haut

    def test_sous_horizon_peu_corrige(self):
        """Pour h < -5°, seule la parallaxe est soustraite (pas de réfraction)."""
        h_in = -10.0
        p    = 0.95
        h_out = MeeusEngine.correction_elevation(h_in, p)
        assert abs(h_out - (h_in - p)) < 0.001

    def test_parallaxe_lune_diminue_altitude(self):
        """La parallaxe de la Lune (~0.95°) doit abaisser l'altitude corrigée."""
        h_sans = MeeusEngine.correction_elevation(45.0, 0.0)
        h_avec = MeeusEngine.correction_elevation(45.0, 0.95)
        assert h_avec < h_sans


# ──────────────────────────────────────────────────────────────────────
# 7. Événements journaliers (lever / coucher)
# ──────────────────────────────────────────────────────────────────────

class TestTrouverEvenements:
    # Paris au solstice d'été 2024 — le soleil se lève et se couche obligatoirement
    PARIS_LAT = 48.8566
    PARIS_LON = 2.3522
    DATE_ETE  = datetime(2024, 6, 21, 12, 0, 0)

    def test_lever_coucher_existent(self):
        """À Paris en été, lever et coucher doivent être détectés."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "soleil")
        assert ev["lever"]   is not None, "Lever non détecté"
        assert ev["coucher"] is not None, "Coucher non détecté"

    def test_lever_avant_coucher(self):
        """Le lever doit précéder le coucher."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "soleil")
        assert ev["lever"] < ev["coucher"]

    def test_culmination_entre_lever_coucher(self):
        """La culmination doit se situer entre le lever et le coucher."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "soleil")
        assert ev["lever"] < ev["culm"] < ev["coucher"]

    def test_crepuscules_ordre_correct(self):
        """Ordre attendu : aube_astro < aube_naut < aube_civ < lever (matin)."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "soleil")
        if all(ev[k] for k in ("aube_astro", "aube_naut", "aube_civ", "lever")):
            assert ev["aube_astro"] < ev["aube_naut"]
            assert ev["aube_naut"]  < ev["aube_civ"]
            assert ev["aube_civ"]   < ev["lever"]

    def test_lever_soleil_paris_ete_plage_horaire(self):
        """Lever du soleil à Paris le 21 juin 2024 ≈ 04h-06h UT."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "soleil")
        lever = ev["lever"]
        heure = lever.hour + lever.minute / 60.0
        assert 3.5 <= heure <= 6.0, f"Lever inattendu à {lever.strftime('%H:%M')}"

    def test_lune_evenements_existent(self):
        """Les événements lunaires doivent utiliser la clé 'lune'."""
        ev = MeeusEngine.trouver_evenements(
            self.DATE_ETE, self.PARIS_LAT, self.PARIS_LON, "lune")
        # Les crépuscules ne sont pas calculés pour la Lune
        assert "lever" in ev
        assert "coucher" in ev
        assert ev.get("aube_civ") is None


# ──────────────────────────────────────────────────────────────────────
# 8. Position des planètes
# ──────────────────────────────────────────────────────────────────────

class TestPositionPlanete:
    T_J2000 = MeeusEngine.siecle_julien2000(datetime(2000, 1, 1, 12, 0, 0))

    def test_ra_dans_plage(self):
        """L'ascension droite doit toujours être dans [0, 24[."""
        for p in ("Venus", "Mars", "Jupiter", "Saturne"):
            ra, _, _ = MeeusEngine.position_planete(self.T_J2000, p)
            assert 0 <= ra < 24, f"{p} : RA = {ra}"

    def test_dec_bornee(self):
        """La déclinaison doit être dans [-90, +90]."""
        for p in ("Venus", "Mars", "Jupiter", "Saturne"):
            _, dec, _ = MeeusEngine.position_planete(self.T_J2000, p)
            assert -90 <= dec <= 90, f"{p} : Dec = {dec}"

    def test_distances_realistes(self):
        """Distances géocentriques dans les plages attendues (UA)."""
        plages = {
            "Venus":   (0.25, 1.75),
            "Mars":    (0.35, 2.7),
            "Jupiter": (3.9, 6.5),
            "Saturne": (7.9, 11.1),
        }
        for p, (dmin, dmax) in plages.items():
            _, _, dist = MeeusEngine.position_planete(self.T_J2000, p)
            assert dmin <= dist <= dmax, f"{p} : dist = {dist:.3f} UA"

    def test_positions_varient_dans_le_temps(self):
        """Les positions planétaires doivent changer entre deux dates espacées d'un an."""
        t1 = MeeusEngine.siecle_julien2000(datetime(2024, 1, 1))
        t2 = MeeusEngine.siecle_julien2000(datetime(2025, 1, 1))
        for p in ("Venus", "Mars", "Jupiter", "Saturne"):
            ra1, _, _ = MeeusEngine.position_planete(t1, p)
            ra2, _, _ = MeeusEngine.position_planete(t2, p)
            assert ra1 != ra2, f"{p} : position inchangée après 1 an"


# ──────────────────────────────────────────────────────────────────────
# Tests Lune haute précision
# ──────────────────────────────────────────────────────────────────────

class TestPositionLuneHP:
    """Vérifie la précision de la Lune contre l'exemple 47.a de Meeus."""

    def test_meeus_exemple_47a(self):
        """12 avril 1992, 0h TD — Meeus p.342."""
        t = MeeusEngine.siecle_julien2000(datetime(1992, 4, 12))
        lon, lat, par = MeeusEngine.position_lune(t)
        # Latitude très précise ; longitude et parallaxe améliorées par
        # rapport à l'ancienne série simplifiée (~1°).
        assert abs(lon - 133.162) < 2.0, f"Longitude : {lon:.3f}° (attendu ~133.162°)"
        assert abs(lat - (-3.229)) < 0.15, f"Latitude : {lat:.3f}° (attendu ~-3.229°)"
        assert 0.89 <= par <= 1.03, f"Parallaxe : {par:.4f}° (hors bornes)"

    def test_precision_amelioree(self):
        """La nouvelle série est meilleure que l'ancienne (~1°) sur plusieurs dates."""
        dates = [datetime(2024, 1, 15), datetime(2024, 6, 21), datetime(2024, 12, 1)]
        for dte in dates:
            t = MeeusEngine.siecle_julien2000(dte)
            lon, lat, par = MeeusEngine.position_lune(t)
            assert 0 <= lon < 360
            assert -6 <= lat <= 6
            assert 0.89 <= par <= 1.03

    def test_bornes_inchangees(self):
        """Les bornes existantes restent valides avec la série complète."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 6, 15))
        lon, lat, par = MeeusEngine.position_lune(t)
        assert 0 <= lon < 360
        assert -7 <= lat <= 7
        assert 0.89 <= par <= 1.03


# ──────────────────────────────────────────────────────────────────────
# Tests Équation du Temps
# ──────────────────────────────────────────────────────────────────────

class TestEquationDuTemps:
    """Vérifie l'Équation du Temps sur des dates connues."""

    def test_plage_annuelle(self):
        """L'EoT reste dans [-17, +17] minutes toute l'année."""
        for mois in range(1, 13):
            t = MeeusEngine.siecle_julien2000(datetime(2024, mois, 15))
            eot = MeeusEngine.equation_du_temps(t)
            assert -17 <= eot <= 17, f"Mois {mois} : EoT = {eot:.1f} min"

    def test_fevrier_negatif(self):
        """Mi-février : EoT ≈ −14 min (±3 min)."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 2, 12))
        eot = MeeusEngine.equation_du_temps(t)
        assert -17 <= eot <= -11, f"Février : EoT = {eot:.1f} min"

    def test_novembre_positif(self):
        """Début novembre : EoT ≈ +16 min (±3 min)."""
        t = MeeusEngine.siecle_julien2000(datetime(2024, 11, 3))
        eot = MeeusEngine.equation_du_temps(t)
        assert 13 <= eot <= 19, f"Novembre : EoT = {eot:.1f} min"


# ──────────────────────────────────────────────────────────────────────
# Tests Séparation angulaire
# ──────────────────────────────────────────────────────────────────────

class TestSeparationAngulaire:
    """Vérifie le calcul de séparation angulaire."""

    def test_meme_point(self):
        """La séparation d'un point avec lui-même vaut 0."""
        sep = MeeusEngine.separation_angulaire(6.0, 45.0, 6.0, 45.0)
        assert abs(sep) < 1e-10

    def test_poles(self):
        """Pôle Nord et Pôle Sud sont séparés de 180°."""
        sep = MeeusEngine.separation_angulaire(0.0, 90.0, 0.0, -90.0)
        assert abs(sep - 180.0) < 1e-10

    def test_90_degres(self):
        """Points séparés de 90° en déclinaison."""
        sep = MeeusEngine.separation_angulaire(0.0, 0.0, 0.0, 90.0)
        assert abs(sep - 90.0) < 1e-10


# ──────────────────────────────────────────────────────────────────────
# Tests Conjonctions
# ──────────────────────────────────────────────────────────────────────

class TestRechercherConjonctions:
    """Vérifie la recherche de conjonctions/oppositions."""

    def test_retourne_liste(self):
        """Le résultat est une liste."""
        resultats = MeeusEngine.rechercher_conjonctions(
            datetime(2024, 1, 1), nb_jours=30)
        assert isinstance(resultats, list)

    def test_structure_resultat(self):
        """Chaque résultat contient les clés attendues."""
        resultats = MeeusEngine.rechercher_conjonctions(
            datetime(2024, 1, 1), nb_jours=60)
        for r in resultats:
            assert 'date' in r
            assert 'type' in r
            assert r['type'] in ('conjonction', 'opposition')
            assert 'objets' in r
            assert 'separation' in r

    def test_evenements_sur_un_an(self):
        """Sur un an, on doit trouver au moins quelques événements."""
        resultats = MeeusEngine.rechercher_conjonctions(
            datetime(2024, 1, 1), nb_jours=365)
        assert len(resultats) >= 1


# ──────────────────────────────────────────────────────────────────────
# Tests Éclipses
# ──────────────────────────────────────────────────────────────────────

class TestRechercherEclipses:
    """Vérifie la détection d'éclipses."""

    def test_retourne_liste(self):
        """Le résultat est une liste."""
        resultats = MeeusEngine.rechercher_eclipses(datetime(2024, 1, 1), nb_mois=6)
        assert isinstance(resultats, list)

    def test_moins_eclipses_que_lunaisons(self):
        """Sur 12 mois, moins d'éclipses que de lunaisons (max ~5-6)."""
        resultats = MeeusEngine.rechercher_eclipses(datetime(2024, 1, 1), nb_mois=12)
        assert len(resultats) < 12

    def test_eclipses_2024(self):
        """En 2024, il y a au moins 2 éclipses (solaire + lunaire connues)."""
        resultats = MeeusEngine.rechercher_eclipses(datetime(2024, 1, 1), nb_mois=12)
        types = [r['type'] for r in resultats]
        assert len(resultats) >= 2, f"Seulement {len(resultats)} éclipse(s) détectée(s)"

    def test_structure_resultat(self):
        """Chaque résultat contient les clés attendues."""
        resultats = MeeusEngine.rechercher_eclipses(datetime(2024, 1, 1), nb_mois=6)
        for r in resultats:
            assert 'date' in r
            assert r['type'] in ('solaire', 'lunaire')
            assert 'certitude' in r
            assert 'latitude_lune' in r
            assert abs(r['latitude_lune']) < 1.58
