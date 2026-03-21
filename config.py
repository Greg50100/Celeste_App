"""
config.py — Configuration et thème visuel de Céleste
=====================================================
Centralise la palette de couleurs et les paramètres globaux de l'application.

Trois thèmes disponibles, tous issus de la palette Catppuccin :
  - Mocha  : dark mode profond (défaut)
  - Frappé : dark mode atténué
  - Latte  : mode clair
"""

# ==========================================================
# 1. PALETTES DE THÈMES (Catppuccin)
# ==========================================================

THEMES = {
    "mocha": {
        "BG_MAIN":    "#1B1B25",
        "BG_PANEL":   "#222230",
        "FG_LABEL":   "#A0A0B0",
        "FG_WHITE":   "#FFFFFF",
        "FG_SUN":     "#F9E2AF",
        "FG_MOON":    "#89B4FA",
        "FG_GREEN":   "#A6E3A1",
        "FG_PURPLE":  "#CBA6F7",
        "FG_RED":     "#F38BA8",
        "BTN_COLOR":  "#89B4FA",
        "GRID_COLOR": "#45475A",
        "appearance": "dark",
    },
    "frappe": {
        "BG_MAIN":    "#303446",
        "BG_PANEL":   "#3B3F52",
        "FG_LABEL":   "#A5ADCE",
        "FG_WHITE":   "#C6D0F5",
        "FG_SUN":     "#E5C890",
        "FG_MOON":    "#8CAAEE",
        "FG_GREEN":   "#A6D189",
        "FG_PURPLE":  "#CA9EE6",
        "FG_RED":     "#E78284",
        "BTN_COLOR":  "#8CAAEE",
        "GRID_COLOR": "#51576D",
        "appearance": "dark",
    },
    "latte": {
        "BG_MAIN":    "#EFF1F5",
        "BG_PANEL":   "#E6E9EF",
        "FG_LABEL":   "#6C6F85",
        "FG_WHITE":   "#4C4F69",
        "FG_SUN":     "#DF8E1D",
        "FG_MOON":    "#1E66F5",
        "FG_GREEN":   "#40A02B",
        "FG_PURPLE":  "#8839EF",
        "FG_RED":     "#D20F39",
        "BTN_COLOR":  "#1E66F5",
        "GRID_COLOR": "#BCC0CC",
        "appearance": "light",
    },
}

# ==========================================================
# 2. CLASSE CONFIG (valeurs actives)
# ==========================================================

class Config:
    """
    Palette de couleurs et paramètres globaux de l'application Céleste.

    Les attributs de classe sont mis à jour dynamiquement par
    ``Config.apply_theme(name)`` en fonction du thème choisi.
    """

    # Valeurs par défaut (Mocha)
    BG_MAIN   = "#1B1B25"
    BG_PANEL  = "#222230"
    FG_LABEL  = "#A0A0B0"
    FG_WHITE  = "#FFFFFF"
    FG_SUN    = "#F9E2AF"
    FG_MOON   = "#89B4FA"
    FG_GREEN  = "#A6E3A1"
    FG_PURPLE = "#CBA6F7"
    FG_RED    = "#F38BA8"
    BTN_COLOR  = "#89B4FA"
    GRID_COLOR = "#45475A"

    # ── Internationalisation ──────────────────
    DEFAULT_LANG = "fr"
    SUPPORTED_LANGS = ["fr", "en", "es", "de"]

    # ── Thème actif ───────────────────────────
    _current_theme = "mocha"

    @classmethod
    def apply_theme(cls, name: str) -> None:
        """Applique un thème Catppuccin par nom."""
        if name not in THEMES:
            name = "mocha"
        cls._current_theme = name
        palette = THEMES[name]
        cls.BG_MAIN   = palette["BG_MAIN"]
        cls.BG_PANEL  = palette["BG_PANEL"]
        cls.FG_LABEL  = palette["FG_LABEL"]
        cls.FG_WHITE  = palette["FG_WHITE"]
        cls.FG_SUN    = palette["FG_SUN"]
        cls.FG_MOON   = palette["FG_MOON"]
        cls.FG_GREEN  = palette["FG_GREEN"]
        cls.FG_PURPLE = palette["FG_PURPLE"]
        cls.FG_RED    = palette["FG_RED"]
        cls.BTN_COLOR  = palette["BTN_COLOR"]
        cls.GRID_COLOR = palette["GRID_COLOR"]

    @classmethod
    def current_theme(cls) -> str:
        return cls._current_theme

    @classmethod
    def appearance_mode(cls) -> str:
        """Retourne 'dark' ou 'light' selon le thème actif."""
        return THEMES.get(cls._current_theme, {}).get(
            "appearance", "dark")
