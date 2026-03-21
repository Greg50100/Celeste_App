"""
main.py — Point d'entrée de l'application Céleste
==================================================
Initialise le système d'internationalisation, puis lance l'interface.

Usage :
    python main.py
    python main.py --lang en
"""

import sys
import customtkinter as ctk
from config import Config
from i18n import switch_lang
import settings as prefs

# ==========================================================
# POINT D'ENTRÉE DE L'APPLICATION CÉLESTE
# ==========================================================

if __name__ == "__main__":
    # ── Langue : settings.json → argument CLI → défaut ─────────────
    prefs.load()
    lang = prefs.get("lang") or Config.DEFAULT_LANG
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1]
        elif arg == "--lang" and sys.argv.index(arg) + 1 < len(sys.argv):
            lang = sys.argv[sys.argv.index(arg) + 1]

    switch_lang(lang)

    # ── Initialisation de la fenêtre ──────────────────────────────────
    root = ctk.CTk()

    from gui import AstroApp
    app = AstroApp(root)

    root.mainloop()
