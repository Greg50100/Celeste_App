"""
utils.py — Utilitaires de formatage pour Céleste
=================================================
Convertit les valeurs numériques brutes (degrés décimaux, heures décimales,
angles de phase) en chaînes de caractères lisibles pour l'interface graphique.
"""

# ==========================================================
# 2. FORMATAGE DES DONNÉES
# ==========================================================
class Formatters:
    """Fonctions utilitaires pour le formatage textuel des coordonnées astronomiques."""

    @staticmethod
    def hms(dh):
        """
        Convertit une Ascension Droite en heures décimales vers le format Heures/Minutes/Secondes.

        Args:
            dh (float): Ascension Droite en heures décimales (valeur absolue utilisée).

        Returns:
            str: Chaîne formatée, ex. "5h 34m 32.0s".
        """
        dh = abs(dh)
        h = int(dh)
        m = int((dh - h) * 60)
        s = round((dh - h - m / 60.0) * 3600.0, 1)
        if s >= 60:
            s = 0.0
            m += 1
        if m >= 60:
            m = 0
            h += 1
        return f"{h}h {m:02d}m {s:04.1f}s"

    @staticmethod
    def dms(dd):
        """
        Convertit une déclinaison en degrés décimaux vers le format Degrés/Minutes/Secondes.

        Args:
            dd (float): Déclinaison en degrés décimaux (peut être négatif).

        Returns:
            str: Chaîne formatée, ex. "-23° 26' 44\"".
        """
        signe = "-" if dd < 0 else ""
        dd = abs(dd)
        d = int(dd)
        m = int((dd - d) * 60)
        s = round((dd - d - m / 60.0) * 3600.0, 0)
        if s >= 60:
            s = 0
            m += 1
        if m >= 60:
            m = 0
            d += 1
        return f"{signe}{d}° {m:02d}' {int(s):02d}\""

    @staticmethod
    def phase_lune(illum, phase_angle):
        """
        Retourne une description textuelle de la phase lunaire avec son emoji.

        La phase est déterminée par l'angle de phase (différence entre la longitude
        écliptique de la Lune et celle du Soleil), découpé en 8 secteurs de 45°.

        Args:
            illum (float): Pourcentage d'illumination de la face visible [0, 100].
            phase_angle (float): Angle de phase en degrés (longitude Lune − longitude Soleil).

        Returns:
            str: Chaîne formatée, ex. "73.2% 🌔 Gibb. Croiss.".
        """
        norm = phase_angle % 360
        if norm < 22.5:
            return f"{illum:.1f}% 🌑 Nouvelle Lune"
        elif norm < 67.5:
            return f"{illum:.1f}% 🌒 Pr. Croissant"
        elif norm < 112.5:
            return f"{illum:.1f}% 🌓 Pr. Quartier"
        elif norm < 157.5:
            return f"{illum:.1f}% 🌔 Gibb. Croiss."
        elif norm < 202.5:
            return f"{illum:.1f}% 🌕 Pleine Lune"
        elif norm < 247.5:
            return f"{illum:.1f}% 🌖 Gibb. Décroiss."
        elif norm < 292.5:
            return f"{illum:.1f}% 🌗 Der. Quartier"
        elif norm < 337.5:
            return f"{illum:.1f}% 🌘 Der. Croissant"
        else:
            return f"{illum:.1f}% 🌑 Nouvelle Lune"