"""
main.py — Point d'entrée de l'application Céleste (PyQt6)
==========================================================
Usage :
    python main.py
    python main.py --lang fr
    python main.py --theme mocha
"""

import sys
import os
from PyQt6.QtWidgets import QApplication

import settings as prefs
from config import Config
from i18n import switch_lang

if __name__ == "__main__":
    prefs.load()

    # ── Thème & langue ─────────────────────────────────────────────────────
    theme = prefs.get("theme") or "mocha"
    lang  = prefs.get("lang")  or Config.DEFAULT_LANG

    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1]
        elif arg == "--lang" and sys.argv.index(arg) + 1 < len(sys.argv):
            lang = sys.argv[sys.argv.index(arg) + 1]
        elif arg.startswith("--theme="):
            theme = arg.split("=", 1)[1]

    Config.apply_theme(theme)
    switch_lang(lang)

    # ── Application Qt ─────────────────────────────────────────────────────
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication(sys.argv)
    # AA_UseHighDpiPixmaps supprime en PyQt6 (HiDPI actif par defaut)

    # Thème Material Design via qt-material
    try:
        from qt_material import apply_stylesheet
        # Mapping palette → thème qt-material
        _mat = {
            "mocha":  "dark_blue.xml",
            "frape":  "dark_purple.xml",
            "latte":  "light_blue.xml",
        }
        qt_theme = _mat.get(theme.replace("\u00e9", "e"), "dark_blue.xml")
        apply_stylesheet(app, theme=qt_theme, extra={
            "density_scale": "0",
            "font_size": "13px",
        })
    except ImportError:
        # qt-material pas installé : fallback Fusion dark
        app.setStyle("Fusion")
        from PyQt6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window,          QColor(Config.BG_MAIN))
        palette.setColor(QPalette.ColorRole.WindowText,      QColor(Config.FG_WHITE))
        palette.setColor(QPalette.ColorRole.Base,            QColor(Config.BG_PANEL))
        palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(Config.BG_MAIN))
        palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(Config.BG_PANEL))
        palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(Config.FG_WHITE))
        palette.setColor(QPalette.ColorRole.Text,            QColor(Config.FG_WHITE))
        palette.setColor(QPalette.ColorRole.Button,          QColor(Config.BG_PANEL))
        palette.setColor(QPalette.ColorRole.ButtonText,      QColor(Config.FG_WHITE))
        palette.setColor(QPalette.ColorRole.Highlight,       QColor(Config.BTN_COLOR))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Config.BG_MAIN))
        app.setPalette(palette)

    from gui import AstroApp
    window = AstroApp()
    window.show()

    # Géolocalisation auto si activée
    if prefs.get("auto_geoloc"):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(800, window.geolocate)

    sys.exit(app.exec())
