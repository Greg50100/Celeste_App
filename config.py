"""
config.py — Configuration and Visual Themes for Céleste
======================================================
Centralizes color palettes (Catppuccin Mocha / Frapé / Latte) and global
application parameters.

Usage:
    from config import Config
    # At startup, call Config.apply_theme(prefs.get("theme")) before building the UI.
"""

# ──────────────────────────────────────────────────────────────────────────────
# THEME PRESETS  (Catppuccin family)
# ──────────────────────────────────────────────────────────────────────────────

_THEMES = {
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
        "CTK_MODE":   "dark",
    },
    "frape": {
        "BG_MAIN":    "#232634",
        "BG_PANEL":   "#292C3C",
        "FG_LABEL":   "#A5ADCE",
        "FG_WHITE":   "#C6D0F5",
        "FG_SUN":     "#EF9F76",
        "FG_MOON":    "#8CAAEE",
        "FG_GREEN":   "#A6D189",
        "FG_PURPLE":  "#CA9EE6",
        "FG_RED":     "#E78284",
        "BTN_COLOR":  "#8CAAEE",
        "GRID_COLOR": "#414559",
        "CTK_MODE":   "dark",
    },
    "latte": {
        "BG_MAIN":    "#EFF1F5",
        "BG_PANEL":   "#E6E9EF",
        "FG_LABEL":   "#5C5F77",
        "FG_WHITE":   "#4C4F69",
        "FG_SUN":     "#FE640B",
        "FG_MOON":    "#1E66F5",
        "FG_GREEN":   "#40A02B",
        "FG_PURPLE":  "#8839EF",
        "FG_RED":     "#D20F39",
        "BTN_COLOR":  "#1E66F5",
        "GRID_COLOR": "#ACB0BE",
        "CTK_MODE":   "light",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG CLASS
# ──────────────────────────────────────────────────────────────────────────────

class Config:
    """Color palette and global parameters for Céleste application."""

    # Default language (ISO 639-1) — overridden by settings.json or --lang CLI arg
    DEFAULT_LANG = "en"

    # Active colors (defaults = mocha)
    BG_MAIN    = "#1B1B25"
    BG_PANEL   = "#222230"
    FG_LABEL   = "#A0A0B0"
    FG_WHITE   = "#FFFFFF"
    FG_SUN     = "#F9E2AF"
    FG_MOON    = "#89B4FA"
    FG_GREEN   = "#A6E3A1"
    FG_PURPLE  = "#CBA6F7"
    FG_RED     = "#F38BA8"
    BTN_COLOR  = "#89B4FA"
    GRID_COLOR = "#45475A"
    CTK_MODE   = "dark"

    @classmethod
    def apply_theme(cls, theme_name: str) -> None:
        """Apply a named theme preset to all Config color attributes."""
        key = (theme_name or "mocha").lower().replace("\u00e9", "e")
        palette = _THEMES.get(key, _THEMES["mocha"])
        for attr, value in palette.items():
            setattr(cls, attr, value)
