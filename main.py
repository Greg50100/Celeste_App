"""
main.py — Point d'entrée de l'application Céleste
==================================================
Initialise la fenêtre CustomTkinter et lance l'application.

Usage :
    python main.py
"""

import customtkinter as ctk
from gui import AstroApp

# ==========================================================
# POINT D'ENTRÉE DE L'APPLICATION CÉLESTE
# ==========================================================

if __name__ == "__main__":
    # Initialisation de la fenêtre racine via CustomTkinter
    root = ctk.CTk()

    # Lancement de l'application
    app = AstroApp(root)

    # Boucle d'événements principale
    root.mainloop()