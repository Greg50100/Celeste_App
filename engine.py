"""
engine.py — Moteur de calcul astronomique de Céleste
=====================================================
Implémente les algorithmes de Jean Meeus (Astronomical Algorithms, 2e éd.)
pour le calcul des positions du Soleil, de la Lune et des planètes, ainsi
que la détection des événements journaliers (lever, coucher, crépuscules).

Ce module est entièrement indépendant de l'interface graphique (modèle MVC).
"""

import math
from datetime import timedelta

# ==========================================================
# 3. MOTEUR MATHÉMATIQUE DE JEAN MEEUS (LE MODÈLE)
# ==========================================================

# Correction de réfraction atmosphérique (Meeus, chap. 16)
# Le Soleil est considéré levé quand son centre est à -0.833° sous l'horizon géométrique
# (0.5° de demi-diamètre apparent + 0.333° de réfraction standard)
_CORRECTION_HORIZON_SOLEIL = 0.833  # degrés

# Constantes de réfraction pour la formule de Bennett (Meeus, chap. 16)
_REFRACTION_A = 10.3   # coefficient angulaire
_REFRACTION_B = 5.11   # décalage angulaire

# Éléments orbitaux moyens à J2000.0 pour les planètes visibles à l'œil nu.
# Format : [L0 (°), L1 (°/siècle), a (UA), e0, e1 (/siècle), i (°), Ω (°), ω̃ (°)]
#   L  = longitude moyenne      a  = demi-grand axe
#   e  = excentricité           i  = inclinaison sur l'écliptique
#   Ω  = longitude du nœud asc. ω̃  = longitude du périhélie
# Source : Meeus, Astronomical Algorithms, 2e éd., Tableau 31.a / App. II.
_ELEMENTS_ORBITAUX = {
    "Venus":   [181.979801,  58517.8156760, 0.72333199,  0.00677323, -0.00004938,  3.39471,  76.68069, 131.53298],
    "Mars":    [355.433275,  19140.2993313, 1.52366231,  0.09341233,  0.00011902,  1.85061,  49.57854, 336.04084],
    "Jupiter": [ 34.351519,   3034.9056606, 5.20336301,  0.04839266, -0.00012880,  1.30530, 100.55615,  14.75385],
    "Saturne": [ 50.077444,   1222.1137943, 9.53707032,  0.05415060, -0.00036762,  2.48446, 113.71504,  92.43194],
}


class MeeusEngine:
    """
    Encapsule tous les calculs astronomiques purs, indépendant de l'interface.

    Toutes les méthodes sont des méthodes de classe ou statiques : aucun état
    interne n'est conservé entre les appels. L'appelant fournit les paramètres
    temporels et géographiques à chaque invocation.

    Référence : Jean Meeus, *Astronomical Algorithms*, 2e éd., Willmann-Bell, 1998.
    """

    @staticmethod
    def mod360(a):
        """Ramène un angle à l'intervalle [0, 360[."""
        return a % 360

    @classmethod
    def jour_julien(cls, dte):
        """
        Calcule le Jour Julien (JD) pour une date-heure donnée.

        Le Jour Julien est le nombre de jours écoulés depuis le 1er janvier 4713 av. J.-C.
        à midi en Temps Universel. Précision : à la seconde près.

        Args:
            dte (datetime): Date et heure en Temps Universel (UT).

        Returns:
            float: Jour Julien correspondant.

        Référence : Meeus, chap. 7.
        """
        y, m, d = dte.year, dte.month, dte.day
        h, mn, s = dte.hour, dte.minute, dte.second
        if m <= 2:
            y -= 1
            m += 12
        a = math.floor(y / 100)
        b = 2 - a + math.floor(a / 4)
        frac_jour = d + (h / 24.0) + (mn / 1440.0) + (s / 86400.0)
        return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + frac_jour + b - 1524.5

    @classmethod
    def siecle_julien2000(cls, dte):
        """
        Calcule le temps en siècles juliens depuis J2000.0 (1.5 janv. 2000, JD 2451545.0).

        Ce paramètre T est utilisé comme variable dans la plupart des séries
        polynomiales de Meeus.

        Args:
            dte (datetime): Date et heure en Temps Universel.

        Returns:
            float: Nombre de siècles juliens depuis J2000.0.
        """
        return (cls.jour_julien(dte) - 2451545.0) / 36525.0

    @classmethod
    def position_soleil(cls, t):
        """
        Calcule la longitude écliptique géocentrique et la distance du Soleil.

        Utilise la série de faible précision de Meeus (précision ~0.01°),
        suffisante pour les applications d'observation visuelle.

        Args:
            t (float): Siècles juliens depuis J2000.0 (via siecle_julien2000).

        Returns:
            tuple[float, float]:
                - l (float): Longitude écliptique apparente du Soleil, en degrés [0, 360[.
                - r (float): Distance Terre-Soleil en Unités Astronomiques (UA).

        Référence : Meeus, chap. 25.
        """
        l0 = cls.mod360(280.46646 + 36000.76983 * t)
        m = cls.mod360(357.52911 + 35999.05029 * t)
        e = 0.016708634 - 0.000042037 * t
        c = (1.914602 - 0.004817 * t) * math.sin(math.radians(m)) + (0.019993 - 0.000101 * t) * math.sin(math.radians(2 * m))
        l = cls.mod360(l0 + c)
        r = 1.00014 * (1 - e**2) / (1 + e * math.cos(math.radians(m + c)))
        return l, r

    @classmethod
    def position_lune(cls, t):
        """
        Calcule la position de la Lune en coordonnées écliptiques géocentriques.

        Utilise la série simplifiée de Meeus (précision ~1°), adéquate pour
        le calcul des événements journaliers et de la phase lunaire.

        Args:
            t (float): Siècles juliens depuis J2000.0 (via siecle_julien2000).

        Returns:
            tuple[float, float, float]:
                - l (float): Longitude écliptique géocentrique, en degrés [0, 360[.
                - b (float): Latitude écliptique géocentrique, en degrés.
                - p (float): Parallaxe équatoriale horizontale, en degrés
                             (utilisée pour la correction de parallaxe et le diamètre apparent).

        Référence : Meeus, chap. 47.
        """
        lp = cls.mod360(218.316 + 481267.881 * t)
        d = cls.mod360(297.85 + 445267.111 * t)
        m = cls.mod360(357.53 + 35999.05 * t)
        mp = cls.mod360(134.96 + 477198.867 * t)
        f = cls.mod360(93.27 + 483202.018 * t)
        l = lp + 6.29 * math.sin(math.radians(mp)) - 1.27 * math.sin(math.radians(mp - 2 * d)) + 0.66 * math.sin(math.radians(2 * d))
        b = 5.13 * math.sin(math.radians(f)) + 0.28 * math.sin(math.radians(mp + f)) - 0.28 * math.sin(math.radians(mp - f))
        p = 0.9508 + 0.0518 * math.cos(math.radians(mp)) + 0.0095 * math.cos(math.radians(mp - 2 * d))
        return cls.mod360(l), b, p

    @classmethod
    def ecliptique_vers_equatorial(cls, l_deg, b_deg, t):
        """
        Convertit des coordonnées écliptiques en coordonnées équatoriales.

        La transformation tient compte de l'obliquité de l'écliptique, qui
        varie lentement avec le temps (précession).

        Args:
            l_deg (float): Longitude écliptique en degrés.
            b_deg (float): Latitude écliptique en degrés.
            t (float): Siècles juliens depuis J2000.0.

        Returns:
            tuple[float, float]:
                - ra (float): Ascension Droite en heures décimales [0, 24[.
                - dec (float): Déclinaison en degrés [-90, +90].

        Référence : Meeus, chap. 13.
        """
        eps = math.radians(23.4392911 - (46.815 * t) / 3600.0)
        l, b = math.radians(l_deg), math.radians(b_deg)
        ra = math.atan2(math.sin(l) * math.cos(eps) - math.tan(b) * math.sin(eps), math.cos(l))
        dec = math.asin(math.sin(b) * math.cos(eps) + math.cos(b) * math.sin(eps) * math.sin(l))
        return cls.mod360(math.degrees(ra)) / 15.0, math.degrees(dec)

    @classmethod
    def equatorial_vers_horizontal(cls, jd, lat, lon, ra_h, dec_deg):
        """
        Convertit des coordonnées équatoriales en coordonnées horizontales locales.

        Calcule d'abord le Temps Sidéral Local (TSL) à partir du Jour Julien
        et des coordonnées géographiques de l'observateur.

        Args:
            jd (float): Jour Julien de l'instant d'observation.
            lat (float): Latitude de l'observateur en degrés (+ = Nord).
            lon (float): Longitude de l'observateur en degrés (+ = Est).
            ra_h (float): Ascension Droite de l'astre en heures décimales.
            dec_deg (float): Déclinaison de l'astre en degrés.

        Returns:
            tuple[float, float]:
                - altitude (float): Hauteur au-dessus de l'horizon en degrés [-90, +90].
                - azimut (float): Azimut en degrés [0, 360[, mesuré depuis le Nord vers l'Est.

        Référence : Meeus, chap. 13.
        """
        theta0 = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
        lst = cls.mod360(theta0 + lon)
        tau = math.radians(lst - ra_h * 15.0)
        phi, delta = math.radians(lat), math.radians(dec_deg)

        h = math.asin(math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(tau))
        y = -math.sin(tau)
        x = math.cos(phi) * math.tan(delta) - math.sin(phi) * math.cos(tau)
        az = cls.mod360(math.degrees(math.atan2(y, x)))
        return math.degrees(h), az

    @staticmethod
    def correction_elevation(h_vraie, parallaxe_deg):
        """
        Corrige l'altitude géométrique d'un astre en tenant compte de la réfraction
        atmosphérique et de la parallaxe.

        - Réfraction : formule de Bennett, précision ~0.07' pour h > 5°.
        - Parallaxe : soustraite (la Lune est significativement plus basse qu'elle
          ne le paraît géométriquement à cause de la parallaxe).

        Args:
            h_vraie (float): Altitude géométrique (non corrigée) en degrés.
            parallaxe_deg (float): Parallaxe équatoriale horizontale en degrés
                                   (0 pour le Soleil, ~0.95° pour la Lune).

        Returns:
            float: Altitude corrigée (réfraction + parallaxe) en degrés.

        Référence : Meeus, chap. 16.
        """
        if h_vraie < -5.0:
            return h_vraie - parallaxe_deg
        r = (1.02 / math.tan(math.radians(h_vraie + _REFRACTION_A / (h_vraie + _REFRACTION_B)))) / 60.0
        return h_vraie + r - parallaxe_deg

    @classmethod
    def trouver_evenements(cls, dte_ref, lat, lon, astre="soleil"):
        """
        Détecte les événements journaliers d'un astre par balayage minute par minute.

        Parcourt les 1440 minutes de la journée et détecte les franchissements
        de seuils d'altitude caractéristiques. La résolution temporelle est d'une minute.

        Seuils détectés :
        - Soleil : lever/coucher (0° + correction 0.833°), aube/crépuscule civil (-6°),
                   nautique (-12°) et astronomique (-18°).
        - Lune   : lever/coucher (altitude corrigée réfraction + parallaxe = 0°).

        Args:
            dte_ref (datetime): N'importe quelle date-heure dans la journée d'intérêt.
            lat (float): Latitude de l'observateur en degrés.
            lon (float): Longitude de l'observateur en degrés.
            astre (str): "soleil" ou "lune". Défaut : "soleil".

        Returns:
            dict: Dictionnaire avec les clés suivantes (valeur None si non détecté) :
                - 'lever'     (datetime): Heure du lever.
                - 'coucher'   (datetime): Heure du coucher.
                - 'culm'      (datetime): Heure de la culmination (altitude maximale).
                - 'aube_civ'  (datetime): Aube civile — Soleil à -6° (soleil uniquement).
                - 'crep_civ'  (datetime): Crépuscule civil — Soleil à -6° (soleil uniquement).
                - 'aube_naut' (datetime): Aube nautique — Soleil à -12° (soleil uniquement).
                - 'crep_naut' (datetime): Crépuscule nautique — Soleil à -12° (soleil uniquement).
                - 'aube_astro'(datetime): Aube astronomique — Soleil à -18° (soleil uniquement).
                - 'crep_astro'(datetime): Crépuscule astronomique — Soleil à -18° (soleil uniquement).
        """
        events = {
            'lever': None, 'coucher': None, 'culm': None,
            'aube_civ': None,  'crep_civ': None,   # Civil       (-6°)
            'aube_naut': None, 'crep_naut': None,   # Nautique   (-12°)
            'aube_astro': None,'crep_astro': None,  # Astronomique(-18°)
        }
        max_alt = -90
        prev_alt = None

        start_day = dte_ref.replace(hour=0, minute=0, second=0, microsecond=0)

        for m in range(1440):
            dt = start_day + timedelta(minutes=m)
            jd = cls.jour_julien(dt)
            t = cls.siecle_julien2000(dt)

            if astre == "soleil":
                s_l, _ = cls.position_soleil(t)
                ra, dec = cls.ecliptique_vers_equatorial(s_l, 0, t)
                alt, _ = cls.equatorial_vers_horizontal(jd, lat, lon, ra, dec)
                alt_test = alt + _CORRECTION_HORIZON_SOLEIL
            else:
                m_l, m_b, m_p = cls.position_lune(t)
                ra, dec = cls.ecliptique_vers_equatorial(m_l, m_b, t)
                alt, _ = cls.equatorial_vers_horizontal(jd, lat, lon, ra, dec)
                alt_test = cls.correction_elevation(alt, m_p)

            # Recherche de culmination
            if alt_test > max_alt:
                max_alt = alt_test
                events['culm'] = dt

            # Détection de franchissements d'horizon et crépuscules
            if prev_alt is not None:
                if prev_alt < 0 and alt_test >= 0:
                    events['lever'] = dt
                elif prev_alt > 0 and alt_test <= 0:
                    events['coucher'] = dt

                if astre == "soleil":
                    if prev_alt < -6 and alt_test >= -6:
                        events['aube_civ'] = dt
                    elif prev_alt > -6 and alt_test <= -6:
                        events['crep_civ'] = dt

                    if prev_alt < -12 and alt_test >= -12:
                        events['aube_naut'] = dt
                    elif prev_alt > -12 and alt_test <= -12:
                        events['crep_naut'] = dt

                    if prev_alt < -18 and alt_test >= -18:
                        events['aube_astro'] = dt
                    elif prev_alt > -18 and alt_test <= -18:
                        events['crep_astro'] = dt

            prev_alt = alt_test

        return events

    @classmethod
    def position_planete(cls, t, nom):
        """
        Calcule la position géocentrique d'une planète en coordonnées équatoriales.

        Utilise les éléments orbitaux moyens de Meeus (App. II) et l'équation de
        Kepler pour obtenir les coordonnées héliocentriques, puis soustrait la
        position de la Terre pour obtenir les coordonnées géocentriques.

        Précision : ~1–2° selon la planète (suffisant pour l'affichage et l'orrery).

        Args:
            t (float): Siècles juliens depuis J2000.0 (via siecle_julien2000).
            nom (str): Nom de la planète — "Venus", "Mars", "Jupiter" ou "Saturne".

        Returns:
            tuple[float, float, float]:
                - ra   (float): Ascension droite en heures décimales [0, 24[.
                - dec  (float): Déclinaison en degrés [-90, +90].
                - dist (float): Distance géocentrique en Unités Astronomiques (UA).

        Référence : Meeus, chap. 33 / Appendice II.
        """
        L0, L1, a, e0, e1, i_deg, omega_deg, peri_deg = _ELEMENTS_ORBITAUX[nom]

        # Éléments à l'instant t
        L   = cls.mod360(L0 + L1 * t)
        e   = e0 + e1 * t
        i   = math.radians(i_deg)
        omega = math.radians(omega_deg)  # longitude du nœud ascendant
        peri  = math.radians(peri_deg)   # longitude du périhélie

        # Anomalie moyenne → résolution de l'équation de Kepler (Newton-Raphson)
        M = math.radians(cls.mod360(L - peri_deg))
        E = M
        for _ in range(50):
            dE = (M - E + e * math.sin(E)) / (1.0 - e * math.cos(E))
            E += dE
            if abs(dE) < 1e-10:
                break

        # Vraie anomalie et distance héliocentrique
        nu = 2.0 * math.atan2(
            math.sqrt(1.0 + e) * math.sin(E / 2.0),
            math.sqrt(1.0 - e) * math.cos(E / 2.0))
        r = a * (1.0 - e * math.cos(E))

        # Longitude écliptique héliocentrique (degrés)
        lam = cls.mod360(math.degrees(peri + nu))

        # Latitude écliptique héliocentrique (approximation à 1er ordre)
        beta = math.degrees(
            math.asin(math.sin(i) * math.sin(math.radians(lam) - omega)))

        # Coordonnées rectangulaires héliocentriques de la planète
        lr, br = math.radians(lam), math.radians(beta)
        xp = r * math.cos(br) * math.cos(lr)
        yp = r * math.cos(br) * math.sin(lr)
        zp = r * math.sin(br)

        # Position héliocentrique de la Terre
        # (longitude_soleil_geocentrique + 180° = longitude_héliocentrique_Terre)
        ls, r_earth = cls.position_soleil(t)
        ls_r = math.radians(cls.mod360(ls + 180.0))
        xe = r_earth * math.cos(ls_r)
        ye = r_earth * math.sin(ls_r)
        ze = 0.0

        # Vecteur géocentrique écliptique
        dx, dy, dz = xp - xe, yp - ye, zp - ze
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        lam_geo  = cls.mod360(math.degrees(math.atan2(dy, dx)))
        beta_geo = math.degrees(math.atan2(dz, math.sqrt(dx * dx + dy * dy)))

        # Conversion écliptique → équatorial
        ra, dec = cls.ecliptique_vers_equatorial(lam_geo, beta_geo, t)
        return ra, dec, dist