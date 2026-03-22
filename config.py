"""
config.py — Configuration and Visual Theme for Céleste
======================================================
Centralizes color palette and global application parameters.

The theme is inspired by Catppuccin Mocha (https://github.com/catppuccin/catppuccin),
a soft and coherent dark mode palette.
"""

# ==========================================================
# 1. CONFIGURATION AND THEMES
# ==========================================================
class Config:
    """
    Color palette and global parameters for Céleste application.

    All colors are hexadecimal strings compatible with
    CustomTkinter and Matplotlib.
    """

    # Backgrounds
    BG_MAIN   = "#1B1B25"   # Main dark background
    BG_PANEL  = "#222230"   # Panels and frames background

    # Text
    FG_LABEL  = "#A0A0B0"   # Labels (light gray)
    FG_WHITE  = "#FFFFFF"   # Important values (pure white)

    # Celestial bodies
    FG_SUN    = "#F9E2AF"   # Sun (yellow/cream)
    FG_MOON   = "#89B4FA"   # Moon (light blue)

    # States and events
    FG_GREEN  = "#A6E3A1"   # Celestial body visible above horizon
    FG_PURPLE = "#CBA6F7"   # Astronomical twilight
    FG_RED    = "#F38BA8"   # Pitch darkness / celestial body below horizon

    # Graphical elements
    BTN_COLOR  = "#89B4FA"  # Primary buttons
    GRID_COLOR = "#45475A"  # Grid lines in charts
