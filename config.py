"""
config.py — Configuration et thème visuel de Céleste
=====================================================
Centralise la palette de couleurs et les paramètres globaux de l'application.

Le thème est inspiré de Catppuccin Mocha (https://github.com/catppuccin/catppuccin),
une palette dark mode douce et cohérente.
"""

# ==========================================================
# 1. CONFIGURATION ET THÈMES
# ==========================================================
class Config:
    """
    Palette de couleurs et paramètres globaux de l'application Céleste.

    Toutes les couleurs sont des chaînes hexadécimales compatibles avec
    CustomTkinter et Matplotlib.
    """

    # Fonds
    BG_MAIN   = "#1B1B25"   # Fond principal sombre
    BG_PANEL  = "#222230"   # Fond des cadres et panneaux

    # Textes
    FG_LABEL  = "#A0A0B0"   # Étiquettes (gris clair)
    FG_WHITE  = "#FFFFFF"   # Valeurs importantes (blanc pur)

    # Astres
    FG_SUN    = "#F9E2AF"   # Soleil (jaune/crème)
    FG_MOON   = "#89B4FA"   # Lune (bleu clair)

    # États et événements
    FG_GREEN  = "#A6E3A1"   # Astre visible au-dessus de l'horizon
    FG_PURPLE = "#CBA6F7"   # Crépuscule astronomique
    FG_RED    = "#F38BA8"   # Nuit noire / astre couché

    # Éléments graphiques
    BTN_COLOR  = "#89B4FA"  # Boutons principaux
    GRID_COLOR = "#45475A"  # Lignes de grille des graphiques