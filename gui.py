"""
gui.py — Interface graphique et contrôleur de Céleste
======================================================
Architecture :
  - Barre latérale gauche  : paramètres (date, lieu, fuseau, favoris)
  - Zone principale droite : onglets Éphémérides / Trajectoires / Carte du Ciel / Planètes
  - Barre de statut bas    : coordonnées, nb étoiles visibles, heure UT

Dépendances :
    customtkinter, matplotlib, tkinter (stdlib)
    config.Config, utils.Formatters, engine.MeeusEngine
"""

import os
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import math
from datetime import datetime, timedelta
import urllib.request
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import Config
from utils import Formatters
from engine import MeeusEngine
from constellations import ETOILES_SUPPLEMENTAIRES, CONSTELLATIONS, ETOILE_CONSTELLATION

# Intervalle de rafraîchissement du mode temps réel (millisecondes)
_INTERVALLE_LIVE_MS = 2000

# Fichier JSON des lieux favoris
_FICHIER_FAVORIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favorites.json")

# Décalages UTC (-12 → +14)
_UTC_OFFSETS = [f"UTC{'+' if i >= 0 else ''}{i}" for i in range(-12, 15)]

# Catalogue d'étoiles : {nom: (RA heures, Dec degrés, magnitude)}
_ETOILES = {
    "Sirius":      ( 6.7523, -16.7161, -1.46),
    "Arcturus":    (14.2612,  19.1822, -0.05),
    "Véga":        (18.6157,  38.7836,  0.03),
    "Capella":     ( 5.2782,  45.9980,  0.08),
    "Rigel":       ( 5.2423,  -8.2016,  0.13),
    "Procyon":     ( 7.6550,   5.2250,  0.34),
    "Betelgeuse":  ( 5.9194,   7.4070,  0.42),
    "Altaïr":      (19.8463,   8.8683,  0.77),
    "Aldébaran":   ( 4.5988,  16.5093,  0.87),
    "Spica":       (13.4199, -11.1613,  1.04),
    "Antarès":     (16.4900, -26.4319,  1.06),
    "Pollux":      ( 7.7553,  28.0262,  1.16),
    "Fomalhaut":   (22.9608, -29.6223,  1.17),
    "Deneb":       (20.6905,  45.2803,  1.25),
    "Régulus":     (10.1395,  11.9672,  1.36),
    "Adhara":      ( 6.9771, -28.9722,  1.50),
    "Castor":      ( 7.5766,  31.8883,  1.58),
    "El Nath":     ( 5.4381,  28.6075,  1.65),
    "Bellatrix":   ( 5.4186,   6.3497,  1.64),
    "Alnilam":     ( 5.6036,  -1.2019,  1.70),
    "Alioth":      (12.9006,  55.9598,  1.76),
    "Alnitak":     ( 5.6791,  -1.9425,  1.77),
    "Mirfak":      ( 3.4054,  49.8614,  1.79),
    "Dubhe":       (11.0623,  61.7508,  1.81),
    "Alkaid":      (13.7924,  49.3133,  1.85),
    "Alhéna":      ( 6.6285,  16.3992,  1.93),
    "Alphard":     ( 9.4597,  -8.6584,  1.99),
    "Hamal":       ( 2.1197,  23.4622,  2.01),
    "Denébola":    (11.8174,  14.5723,  2.14),
    "Mérak":       (11.0307,  56.3824,  2.37),
    "Phécda":      (11.8966,  53.6948,  2.44),
    "Polaris":     ( 2.5303,  89.2641,  1.97),
}
_ETOILES.update(ETOILES_SUPPLEMENTAIRES)


class AstroApp:
    """Application principale Céleste — Vue et Contrôleur MVC."""

    def __init__(self, root):
        self.root = root
        self.root.title("Céleste — Observatoire Astronomique")
        self.root.geometry("1280x800")
        self.root.minsize(1100, 700)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root.configure(bg=Config.BG_MAIN)

        # État
        self.live_mode = False
        self.last_cache_key = ""
        self.s_events = {}
        self.m_events = {}
        self.heures = []
        self.alt_soleil = []
        self.alt_lune = []
        self.utc_offset = 0
        self.favoris = self._charger_favoris()
        self.etoiles_visibles = []
        self._soleil_data = {}
        self._lune_data = {}
        self._popup_detail = None
        self.planet_labels = {}    # rempli par setup_ui → onglet Planètes

        self.setup_ui()
        self.calculer()

    # ──────────────────────────────────────────────────────────────────
    # INTERFACE
    # ──────────────────────────────────────────────────────────────────

    def setup_ui(self):
        """Construit l'interface : barre de statut + sidebar + onglets principaux."""

        # ── Barre de statut (packée en premier = ancrage bas) ──────────
        sb = ctk.CTkFrame(self.root, fg_color=Config.BG_PANEL, corner_radius=0, height=24)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)

        self.lbl_status_pos = ctk.CTkLabel(sb, text="📍 —",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_pos.pack(side=tk.LEFT, padx=14)

        self.lbl_status_stars = ctk.CTkLabel(sb, text="",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_stars.pack(side=tk.LEFT, padx=10)

        self.lbl_status_time = ctk.CTkLabel(sb, text="UT : —",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_time.pack(side=tk.RIGHT, padx=14)

        # ── Sidebar gauche (paramètres) ────────────────────────────────
        sidebar = ctk.CTkFrame(self.root, fg_color=Config.BG_MAIN,
                               corner_radius=0, width=290)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=8)
        sidebar.pack_propagate(False)

        # En-tête logo
        hdr = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 5))

        ctk.CTkLabel(hdr, text="✨ CÉLESTE", text_color=Config.FG_MOON,
                     font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        ctk.CTkLabel(hdr, text="v3.0", text_color=Config.GRID_COLOR,
                     font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT, pady=(12, 0))

        self.btn_live = ctk.CTkButton(hdr, text="⏱ LIVE", command=self.toggle_live,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=76, font=("Segoe UI", 11))
        self.btn_live.pack(side=tk.RIGHT, padx=10)

        # Section Paramètres
        p = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        p.pack(fill=tk.X, padx=8, pady=5)

        ctk.CTkLabel(p, text="⚙  PARAMÈTRES", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 10, "bold")).grid(
                     row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(8, 5))

        # Date
        ctk.CTkLabel(p, text="Date / Heure UT :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=1, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_date = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_date.insert(0, datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        self.entry_date.grid(row=1, column=1, columnspan=2, pady=3, padx=(4, 10), sticky=tk.EW)

        # Latitude
        ctk.CTkLabel(p, text="Latitude :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=2, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_lat = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_lat.insert(0, "49.6333")
        self.entry_lat.grid(row=2, column=1, columnspan=2, pady=3, padx=(4, 10), sticky=tk.EW)

        # Longitude
        ctk.CTkLabel(p, text="Longitude :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=3, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_lon = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_lon.insert(0, "-1.6167")
        self.entry_lon.grid(row=3, column=1, pady=3, padx=(4, 4), sticky=tk.EW)

        self.btn_geo = ctk.CTkButton(p, text="📍", command=self.geolocaliser,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=32, font=("Segoe UI", 13))
        self.btn_geo.grid(row=3, column=2, padx=(2, 10))

        # Fuseau
        ctk.CTkLabel(p, text="Fuseau :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=4, column=0, sticky=tk.W, padx=10, pady=3)
        self.offset_menu = ctk.CTkOptionMenu(p, values=_UTC_OFFSETS,
            command=self._on_offset_change, font=("Segoe UI", 11))
        self.offset_menu.set("UTC+0")
        self.offset_menu.grid(row=4, column=1, columnspan=2, pady=3, padx=(4, 10), sticky=tk.EW)

        p.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(p, text="⚡  CALCULER", command=self.calculer,
            fg_color=Config.BTN_COLOR, text_color=Config.BG_MAIN,
            font=("Segoe UI", 12, "bold")).grid(
            row=5, column=0, columnspan=3, pady=(10, 8), sticky=tk.EW, padx=10)

        for w in (self.entry_date, self.entry_lat, self.entry_lon):
            w.bind("<Return>", lambda e: self.calculer())

        # Section Favoris
        fav = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        fav.pack(fill=tk.X, padx=8, pady=5)

        ctk.CTkLabel(fav, text="📌  LIEUX FAVORIS", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 10, "bold")).grid(
                     row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(8, 5))

        noms = list(self.favoris.keys())
        self.combo_favoris = ctk.CTkComboBox(fav,
            values=noms if noms else [""],
            command=self.appliquer_lieu, font=("Segoe UI", 11))
        self.combo_favoris.set("📍 Cherbourg-en-Cotentin")
        self.combo_favoris.grid(row=1, column=0, padx=(10, 4), pady=(0, 8), sticky=tk.EW)

        ctk.CTkButton(fav, text="💾", command=self.sauvegarder_lieu,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=32, font=("Segoe UI", 13)).grid(row=1, column=1, padx=2)
        ctk.CTkButton(fav, text="🗑", command=self.supprimer_lieu,
            fg_color="transparent", border_color=Config.FG_RED, border_width=1,
            text_color=Config.FG_RED, width=32, font=("Segoe UI", 13)).grid(row=1, column=2, padx=(2, 10))

        fav.grid_columnconfigure(0, weight=1)

        # ── Zone de contenu principal ──────────────────────────────────
        content = ctk.CTkFrame(self.root, fg_color=Config.BG_MAIN, corner_radius=0)
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        tabs = ctk.CTkTabview(content,
            fg_color=Config.BG_PANEL,
            segmented_button_fg_color=Config.BG_MAIN,
            segmented_button_selected_color=Config.BTN_COLOR,
            segmented_button_selected_hover_color=Config.FG_MOON,
            anchor="nw")
        tabs.pack(fill=tk.BOTH, expand=True)

        # ── Onglet 1 : Éphémérides ────────────────────────────────────
        tab_eph = tabs.add("☀️🌙  Éphémérides")

        col_sun = ctk.CTkFrame(tab_eph, fg_color=Config.BG_MAIN, corner_radius=8)
        col_sun.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 3), pady=6)

        # En-tête Soleil
        sun_hdr = ctk.CTkFrame(col_sun, fg_color="#2A2A1A", corner_radius=6)
        sun_hdr.pack(fill=tk.X, padx=6, pady=(6, 0))
        ctk.CTkLabel(sun_hdr, text="  ☀️  SOLEIL", font=("Segoe UI", 15, "bold"),
                     text_color=Config.FG_SUN).pack(side=tk.LEFT, padx=10, pady=8)
        self.lbl_sun_vis = ctk.CTkLabel(sun_hdr, text="",
            font=("Segoe UI", 11, "bold"), text_color=Config.FG_GREEN)
        self.lbl_sun_vis.pack(side=tk.RIGHT, padx=10)

        sun_data = ctk.CTkScrollableFrame(col_sun, fg_color="transparent")
        sun_data.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        sun_fields = [
            ("RA",        "Asc. Droite"),
            ("Dec",       "Déclinaison"),
            ("Alt",       "Hauteur"),
            ("Az",        "Azimut"),
            ("EoT",       "Éq. du Temps"),
            ("DawnAstro", "Aube Astro  −18°"),
            ("DawnNaut",  "Aube Naut.  −12°"),
            ("Dawn",      "Aube Civile  −6°"),
            ("Rise",      "Lever"),
            ("Transit",   "Culmination"),
            ("Set",       "Coucher"),
            ("Dusk",      "Crép. Civil  −6°"),
            ("DuskNaut",  "Crép. Naut. −12°"),
            ("DuskAstro", "Crép. Astro −18°"),
        ]
        self.sun_labels = self._build_data_grid(sun_data, Config.FG_SUN, sun_fields)

        # Séparateur vertical
        ctk.CTkFrame(tab_eph, fg_color=Config.GRID_COLOR, width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=12)

        col_moon = ctk.CTkFrame(tab_eph, fg_color=Config.BG_MAIN, corner_radius=8)
        col_moon.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3, 6), pady=6)

        # En-tête Lune
        moon_hdr = ctk.CTkFrame(col_moon, fg_color="#1A1A2A", corner_radius=6)
        moon_hdr.pack(fill=tk.X, padx=6, pady=(6, 0))
        ctk.CTkLabel(moon_hdr, text="  🌙  LUNE", font=("Segoe UI", 15, "bold"),
                     text_color=Config.FG_MOON).pack(side=tk.LEFT, padx=10, pady=8)
        self.lbl_moon_vis = ctk.CTkLabel(moon_hdr, text="",
            font=("Segoe UI", 11, "bold"), text_color=Config.FG_GREEN)
        self.lbl_moon_vis.pack(side=tk.RIGHT, padx=10)

        moon_data = ctk.CTkScrollableFrame(col_moon, fg_color="transparent")
        moon_data.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        moon_fields = [
            ("RA",      "Asc. Droite"),
            ("Dec",     "Déclinaison"),
            ("Alt",     "Hauteur"),
            ("Az",      "Azimut"),
            ("Illum",   "Phase Lunaire"),
            ("Rise",    "Lever"),
            ("Transit", "Culmination"),
            ("Set",     "Coucher"),
        ]
        self.moon_labels = self._build_data_grid(moon_data, Config.FG_MOON, moon_fields)

        # ── Onglet 2 : Trajectoires ───────────────────────────────────
        tab_traj = tabs.add("📈  Trajectoires")

        self.fig1 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax1 = self.fig1.add_subplot(111, facecolor=Config.BG_PANEL)
        self.fig1.subplots_adjust(left=0.07, right=0.97, top=0.93, bottom=0.08)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=tab_traj)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.annot = self.ax1.annotate("", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round4,pad=0.6", fc=Config.BG_PANEL,
                      ec=Config.FG_LABEL, lw=1),
            color="white", zorder=10, fontfamily="monospace")
        self.annot.set_visible(False)
        self.canvas1.mpl_connect("motion_notify_event", self.on_hover)

        # ── Onglet 3 : Carte du Ciel ──────────────────────────────────
        tab_carte = tabs.add("🔭  Carte du Ciel")

        self.fig2 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax2 = self.fig2.add_subplot(111, projection='polar',
                                         facecolor=Config.BG_PANEL)
        self.fig2.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.05)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=tab_carte)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.annot2 = self.ax2.annotate("", xy=(0, 0), xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round4,pad=0.5", fc=Config.BG_PANEL,
                      ec=Config.FG_MOON, lw=1),
            color="white", zorder=10, fontfamily="monospace", fontsize=8)
        self.annot2.set_visible(False)
        self.canvas2.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas2.mpl_connect("button_press_event", self._on_click_carte)

        # ── Onglet 4 : Planètes ───────────────────────────────────────
        tab_pl = tabs.add("🪐  Planètes")

        # Colonne gauche : cartes éphémérides planétaires
        left_pl = ctk.CTkFrame(tab_pl, fg_color=Config.BG_MAIN, corner_radius=0)
        left_pl.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(4, 2), pady=4)
        left_pl.configure(width=310)
        left_pl.pack_propagate(False)

        _PLANETES_CFG = [
            ("Venus",   "♀  VÉNUS",   "#D4C060", "#28271A"),
            ("Mars",    "♂  MARS",    "#E07050", "#2A1A18"),
            ("Jupiter", "♃  JUPITER", "#C8A870", "#28231A"),
            ("Saturne", "♄  SATURNE", "#C0C060", "#23251A"),
        ]
        self.planet_labels = {}
        pl_fields = [
            ("RA",   "Asc. Droite"),
            ("Dec",  "Déclinaison"),
            ("Alt",  "Hauteur"),
            ("Az",   "Azimut"),
            ("Dist", "Distance (UA)"),
        ]
        for pname, ptitle, pcolor, pbg in _PLANETES_CFG:
            card = ctk.CTkFrame(left_pl, fg_color=Config.BG_PANEL, corner_radius=8)
            card.pack(fill=tk.X, padx=6, pady=4)
            phdr = ctk.CTkFrame(card, fg_color=pbg, corner_radius=6)
            phdr.pack(fill=tk.X)
            ctk.CTkLabel(phdr, text=f"  {ptitle}",
                font=("Segoe UI", 13, "bold"), text_color=pcolor
                ).pack(side=tk.LEFT, padx=8, pady=5)
            vis_lbl = ctk.CTkLabel(phdr, text="",
                font=("Segoe UI", 10, "bold"), text_color=Config.FG_GREEN)
            vis_lbl.pack(side=tk.RIGHT, padx=8)
            data_frame = ctk.CTkFrame(card, fg_color="transparent")
            data_frame.pack(fill=tk.X, padx=2, pady=2)
            lbls = self._build_data_grid(data_frame, pcolor, pl_fields)
            lbls["_vis"] = vis_lbl
            self.planet_labels[pname] = lbls

        # Colonne droite : orrery (vue de dessus du système solaire)
        right_pl = ctk.CTkFrame(tab_pl, fg_color=Config.BG_MAIN, corner_radius=0)
        right_pl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 4), pady=4)

        self.fig3 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax3  = self.fig3.add_subplot(111, aspect='equal',
                                          facecolor=Config.BG_PANEL)
        self.fig3.subplots_adjust(left=0.05, right=0.97, top=0.93, bottom=0.05)
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=right_pl)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ── Onglet 5 : Événements astronomiques ──────────────────────
        tab_evt = tabs.add("📅  Événements")

        btn_frame = ctk.CTkFrame(tab_evt, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=10, pady=(10, 4))

        ctk.CTkButton(btn_frame, text="🔍  Rechercher Éclipses (12 mois)",
                      command=self._rechercher_eclipses_gui,
                      fg_color=Config.BTN_COLOR, height=32,
                      font=ctk.CTkFont(size=12)).pack(side=tk.LEFT, padx=(0, 8))
        ctk.CTkButton(btn_frame, text="🔍  Rechercher Conjonctions (12 mois)",
                      command=self._rechercher_conjonctions_gui,
                      fg_color=Config.FG_PURPLE, height=32,
                      font=ctk.CTkFont(size=12)).pack(side=tk.LEFT)

        self.evt_scroll = ctk.CTkScrollableFrame(tab_evt, fg_color=Config.BG_MAIN,
                                                  corner_radius=8)
        self.evt_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        ctk.CTkLabel(self.evt_scroll, text="Cliquez sur un bouton pour lancer la recherche.",
                     text_color=Config.FG_LABEL, font=ctk.CTkFont(size=11)).pack(pady=20)

    def _build_data_grid(self, parent, color, fields):
        """
        Crée une grille de lignes étiquette / valeur dans un frame parent.

        Chaque ligne alterne légèrement de fond pour la lisibilité.
        Retourne un dict {clé: CTkLabel valeur}.
        """
        TIME_KEYS = {"Rise", "Transit", "Set", "Dawn", "Dusk", "Illum",
                     "DawnNaut", "DuskNaut", "DawnAstro", "DuskAstro"}
        labels = {}
        row_colors = [Config.BG_PANEL, Config.BG_MAIN]

        for i, (key, text) in enumerate(fields):
            bg = row_colors[i % 2]
            row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=4)
            row.pack(fill=tk.X, pady=1, padx=2)

            ctk.CTkLabel(row, text=text, text_color=Config.FG_LABEL,
                         font=("Segoe UI", 11), anchor="w",
                         width=150).pack(side=tk.LEFT, padx=(10, 4), pady=4)

            val_color = Config.FG_WHITE if key in TIME_KEYS else color
            lbl = ctk.CTkLabel(row, text="—", text_color=val_color,
                               font=("Consolas", 11, "bold"), anchor="e")
            lbl.pack(side=tk.RIGHT, padx=10, pady=4)
            labels[key] = lbl

        return labels

    # ──────────────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────
    # PLANÈTES
    # ──────────────────────────────────────────────────────────────────

    def _calculer_planetes(self, dte, jd, t, lat, lon):
        """Calcule et affiche les éphémérides des 4 planètes + met à jour l'orrery."""
        if not self.planet_labels:
            return

        # Données héliocentrique pour l'orrery
        from engine import _ELEMENTS_ORBITAUX
        helio = {}

        for pname, lb in self.planet_labels.items():
            ra, dec, dist = MeeusEngine.position_planete(t, pname)
            p_alt, p_az = MeeusEngine.equatorial_vers_horizontal(jd, lat, lon, ra, dec)

            lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
            lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
            lb["Alt"].configure(text=f"{p_alt:.2f}°")
            lb["Az"].configure(text=f"{p_az:.2f}°")
            lb["Dist"].configure(text=f"{dist:.4f} UA")

            if p_alt > 0:
                lb["_vis"].configure(text="🌟 VISIBLE", text_color=Config.FG_GREEN)
            else:
                lb["_vis"].configure(text="⬇ COUCHÉE", text_color=Config.FG_RED)

            # Longitude héliocentrique pour l'orrery
            L0, L1, a, *_ = _ELEMENTS_ORBITAUX[pname]
            L_deg = MeeusEngine.mod360(L0 + L1 * t)
            helio[pname] = (a, math.radians(L_deg))

        self._tracer_orrery(t, helio)

    def _tracer_orrery(self, t, helio):
        """Dessine la vue de dessus du système solaire (orrery 2D)."""
        ax = self.ax3
        ax.clear()
        ax.set_facecolor(Config.BG_PANEL)
        ax.set_title("Système Solaire — Vue de dessus (J2000.0)", color=Config.FG_WHITE,
                     fontsize=10, pad=8)
        ax.tick_params(colors=Config.FG_LABEL, labelsize=8)
        for sp in ax.spines.values():
            sp.set_color(Config.GRID_COLOR)
        ax.grid(color=Config.GRID_COLOR, linestyle=":", alpha=0.4)

        # Soleil
        ax.plot(0, 0, "o", color=Config.FG_SUN, markersize=14, zorder=5)
        ax.annotate("Soleil", xy=(0, 0), xytext=(0.18, 0.05),
            color=Config.FG_SUN, fontsize=8)

        # Terre
        s_l, r_e = MeeusEngine.position_soleil(t)
        l_e = math.radians(MeeusEngine.mod360(s_l + 180))
        xe, ye = r_e * math.cos(l_e), r_e * math.sin(l_e)
        # Orbite de la Terre
        theta = [i * math.tau / 360 for i in range(361)]
        ax.plot([r_e * math.cos(a) for a in theta],
                [r_e * math.sin(a) for a in theta],
                color=Config.FG_MOON, linewidth=0.5, alpha=0.3)
        ax.plot(xe, ye, "o", color=Config.FG_MOON, markersize=7, zorder=5)
        ax.annotate("Terre", xy=(xe, ye), xytext=(xe + 0.1, ye + 0.1),
            color=Config.FG_MOON, fontsize=8)

        _PLANET_COLORS = {
            "Venus":   "#D4C060",
            "Mars":    "#E07050",
            "Jupiter": "#C8A870",
            "Saturne": "#C0C060",
        }
        _PLANET_SIZES = {"Venus": 6, "Mars": 6, "Jupiter": 9, "Saturne": 8}

        for pname, (a, l_rad) in helio.items():
            xp, yp = a * math.cos(l_rad), a * math.sin(l_rad)
            color = _PLANET_COLORS[pname]
            # Orbite
            ax.plot([a * math.cos(ang) for ang in theta],
                    [a * math.sin(ang) for ang in theta],
                    color=color, linewidth=0.5, alpha=0.25)
            # Planète
            ax.plot(xp, yp, "o", color=color,
                    markersize=_PLANET_SIZES[pname], zorder=4)
            ax.annotate(pname, xy=(xp, yp), xytext=(xp + 0.1, yp + 0.15),
                color=color, fontsize=8)

        limit = 11.0
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_xlabel("UA", color=Config.FG_LABEL, fontsize=8)
        ax.set_ylabel("UA", color=Config.FG_LABEL, fontsize=8)
        self.canvas3.draw_idle()

    # ──────────────────────────────────────────────────────────────────
    # STATUT
    # ──────────────────────────────────────────────────────────────────

    def _update_status(self, lat, lon, dte):
        """Met à jour la barre de statut (coordonnées, étoiles, heure UT)."""
        self.lbl_status_pos.configure(
            text=f"📍 Lat: {lat:+.4f}°  Lon: {lon:+.4f}°")
        n = len(self.etoiles_visibles)
        self.lbl_status_stars.configure(
            text=f"★ {n} étoile{'s' if n != 1 else ''} visible{'s' if n != 1 else ''}")
        self.lbl_status_time.configure(
            text=f"UT : {dte.strftime('%d/%m/%Y  %H:%M:%S')}")

    # ──────────────────────────────────────────────────────────────────
    # LIEUX FAVORIS
    # ──────────────────────────────────────────────────────────────────

    def _charger_favoris(self):
        """Charge favorites.json. Retourne {} si absent."""
        if os.path.exists(_FICHIER_FAVORIS):
            with open(_FICHIER_FAVORIS, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _sauvegarder_favoris(self):
        """Écrit self.favoris dans favorites.json."""
        with open(_FICHIER_FAVORIS, "w", encoding="utf-8") as f:
            json.dump(self.favoris, f, ensure_ascii=False, indent=2)

    def _rafraichir_combo_favoris(self):
        noms = list(self.favoris.keys())
        self.combo_favoris.configure(values=noms if noms else [""])

    def sauvegarder_lieu(self):
        """Demande un nom et sauvegarde les coordonnées courantes."""
        try:
            lat = float(self.entry_lat.get().replace(",", "."))
            lon = float(self.entry_lon.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erreur", "Coordonnées invalides.")
            return
        nom = simpledialog.askstring("Sauvegarder le lieu", "Nom :", parent=self.root)
        if nom and nom.strip():
            nom = nom.strip()
            self.favoris[nom] = {"lat": lat, "lon": lon}
            self._sauvegarder_favoris()
            self._rafraichir_combo_favoris()
            self.combo_favoris.set(nom)

    def supprimer_lieu(self):
        """Supprime le lieu sélectionné."""
        nom = self.combo_favoris.get()
        if nom in self.favoris:
            del self.favoris[nom]
            self._sauvegarder_favoris()
            self._rafraichir_combo_favoris()
            self.combo_favoris.set("")

    def appliquer_lieu(self, choix):
        """Applique les coordonnées du lieu sélectionné et recalcule."""
        if choix in self.favoris:
            lieu = self.favoris[choix]
            self.entry_lat.delete(0, tk.END)
            self.entry_lat.insert(0, str(lieu["lat"]))
            self.entry_lon.delete(0, tk.END)
            self.entry_lon.insert(0, str(lieu["lon"]))
            self.calculer()

    # ──────────────────────────────────────────────────────────────────
    # FUSEAU HORAIRE
    # ──────────────────────────────────────────────────────────────────

    def _on_offset_change(self, choix):
        val = choix.replace("UTC", "").replace("+", "")
        self.utc_offset = int(val)
        self.calculer()

    def _fmt_event(self, dt):
        """Formate une heure UT en heure locale (offset appliqué). Retourne '--:--' si None."""
        if dt is None:
            return "--:--"
        return (dt + timedelta(hours=self.utc_offset)).strftime("%H:%M")

    # ──────────────────────────────────────────────────────────────────
    # INTERACTIONS
    # ──────────────────────────────────────────────────────────────────

    def on_hover(self, event):
        """Tooltip sur le graphique 24h (ax1) et la carte polaire (ax2)."""
        c1, c2 = False, False

        if event.inaxes == self.ax1:
            x = event.xdata
            if x is not None and self.heures:
                idx = min(range(len(self.heures)), key=lambda i: abs(self.heures[i] - x))
                h = self.heures[idx]
                a_s, a_m = self.alt_soleil[idx], self.alt_lune[idx]
                self.annot.xy = (h, max(a_s, a_m))
                self.annot.set_text(
                    f"UT : {h:02d}h00\nSoleil : {a_s:+.1f}°\nLune   : {a_m:+.1f}°")
                self.annot.set_visible(True)
                c1 = True
            if self.annot2.get_visible():
                self.annot2.set_visible(False)
                c2 = True

        elif event.inaxes == self.ax2:
            if event.xdata is not None and self.etoiles_visibles:
                xm = event.ydata * math.cos(event.xdata)
                ym = event.ydata * math.sin(event.xdata)
                best, bd = None, float('inf')
                for item in self.etoiles_visibles:
                    _, _, az, r, _, _ = item
                    d = math.hypot(xm - r * math.cos(az), ym - r * math.sin(az))
                    if d < bd:
                        bd, best = d, item
                if bd < 7 and best:
                    nom, mag, az, r, alt, azd = best
                    self.annot2.xy = (az, r)
                    self.annot2.set_text(
                        f"★ {nom}\nAlt : {alt:.1f}°  Az : {azd:.1f}°\nMag : {mag:+.2f}")
                    self.annot2.set_visible(True)
                    c2 = True
                elif self.annot2.get_visible():
                    self.annot2.set_visible(False)
                    c2 = True
            if self.annot.get_visible():
                self.annot.set_visible(False)
                c1 = True

        else:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                c1 = True
            if self.annot2.get_visible():
                self.annot2.set_visible(False)
                c2 = True

        if c1:
            self.canvas1.draw_idle()
        if c2:
            self.canvas2.draw_idle()

    def _on_click_carte(self, event):
        """Clic sur la carte du ciel — ouvre le popup de détail."""
        if event.inaxes != self.ax2 or event.xdata is None:
            return

        xm = event.ydata * math.cos(event.xdata)
        ym = event.ydata * math.sin(event.xdata)

        best, bd = None, float('inf')
        for item in self.etoiles_visibles:
            _, _, az, r, _, _ = item
            d = math.hypot(xm - r * math.cos(az), ym - r * math.sin(az))
            if d < bd:
                bd, best = d, item

        best_type = "etoile"
        for obj in (self._soleil_data, self._lune_data):
            if obj and obj.get('alt', -90) > 0:
                az_r = math.radians(obj['az'])
                r = 90 - obj['alt']
                d = math.hypot(xm - r * math.cos(az_r), ym - r * math.sin(az_r))
                if d < bd:
                    bd, best, best_type = d, obj, "astre"

        if bd > 10:
            return

        if best_type == "etoile" and isinstance(best, tuple):
            nom, mag, _, _, alt, azd = best
            ra_h, dec_d, _ = _ETOILES[nom]
            consts = ETOILE_CONSTELLATION.get(nom, [])
            self._afficher_detail_objet(
                nom=nom, icone="★",
                ra=ra_h, dec=dec_d, alt=alt, az=azd, mag=mag,
                constellation=", ".join(consts) if consts else "—")
        elif best_type == "astre" and isinstance(best, dict):
            icone = "☀" if best['nom'] == "Soleil" else "☾"
            self._afficher_detail_objet(
                nom=best['nom'], icone=icone,
                ra=best.get('ra'), dec=best.get('dec'),
                alt=best['alt'], az=best['az'], mag=None,
                constellation=None, extra=best)

    def _afficher_detail_objet(self, nom, icone, ra, dec, alt, az, mag,
                                constellation, extra=None):
        """Affiche un popup CTkToplevel avec les détails d'un objet céleste."""
        if self._popup_detail is not None:
            try:
                self._popup_detail.destroy()
            except Exception:
                pass

        popup = ctk.CTkToplevel(self.root)
        popup.title(f"Détails — {nom}")
        popup.geometry("320x300")
        popup.configure(fg_color=Config.BG_PANEL)
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        self._popup_detail = popup

        ctk.CTkLabel(popup, text=f"{icone}  {nom}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=Config.FG_WHITE).pack(pady=(12, 4))

        frame = ctk.CTkFrame(popup, fg_color=Config.BG_MAIN, corner_radius=8)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        infos = []
        if constellation:
            infos.append(("Constellation", constellation))
        if ra is not None:
            infos.append(("Asc. Droite", Formatters.hms(ra)))
        if dec is not None:
            infos.append(("Déclinaison", Formatters.dms(dec)))
        infos.append(("Altitude", f"{alt:+.2f}°"))
        infos.append(("Azimut", f"{az:.2f}°"))
        if mag is not None:
            infos.append(("Magnitude", f"{mag:+.2f}"))
        if alt > 0:
            infos.append(("Visibilité", "Au-dessus de l'horizon"))
        if extra and 'illum' in extra:
            infos.append(("Illumination", f"{extra['illum']:.1f} %"))
            infos.append(("Phase", Formatters.phase_lune(
                extra['illum'], extra['phase'])))

        for label, value in infos:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill=tk.X, padx=8, pady=2)
            ctk.CTkLabel(row, text=f"{label} :",
                         text_color=Config.FG_LABEL,
                         font=ctk.CTkFont(size=11),
                         anchor="w", width=120).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=str(value),
                         text_color=Config.FG_WHITE,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side=tk.LEFT)

        ctk.CTkButton(popup, text="Fermer", command=popup.destroy,
                      fg_color=Config.BTN_COLOR, width=100,
                      height=28).pack(pady=(4, 10))

    # ──────────────────────────────────────────────────────────────────
    # ONGLET ÉVÉNEMENTS
    # ──────────────────────────────────────────────────────────────────

    def _vider_evt_scroll(self):
        """Supprime tous les widgets du scrollframe des événements."""
        for w in self.evt_scroll.winfo_children():
            w.destroy()

    def _ajouter_evt_ligne(self, date_str, texte, couleur):
        """Ajoute une ligne de résultat dans le scrollframe."""
        row = ctk.CTkFrame(self.evt_scroll, fg_color=Config.BG_PANEL, corner_radius=6)
        row.pack(fill=tk.X, pady=2, padx=4)
        ctk.CTkLabel(row, text=date_str, text_color=Config.FG_WHITE,
                     font=ctk.CTkFont(size=11, weight="bold"), width=140,
                     anchor="w").pack(side=tk.LEFT, padx=(10, 6), pady=6)
        ctk.CTkLabel(row, text=texte, text_color=couleur,
                     font=ctk.CTkFont(size=11), anchor="w").pack(
                         side=tk.LEFT, padx=(0, 10), pady=6)

    def _rechercher_eclipses_gui(self):
        """Lance la recherche d'éclipses et affiche les résultats."""
        self._vider_evt_scroll()
        try:
            s = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            dte = datetime.utcnow()

        ctk.CTkLabel(self.evt_scroll, text="Recherche en cours…",
                     text_color=Config.FG_LABEL).pack(pady=10)
        self.root.update_idletasks()
        self._vider_evt_scroll()

        resultats = MeeusEngine.rechercher_eclipses(dte, nb_mois=12)

        if not resultats:
            ctk.CTkLabel(self.evt_scroll, text="Aucune éclipse détectée sur 12 mois.",
                         text_color=Config.FG_LABEL).pack(pady=20)
            return

        ctk.CTkLabel(self.evt_scroll,
                     text=f"🌑  {len(resultats)} éclipse(s) trouvée(s) sur 12 mois",
                     text_color=Config.FG_WHITE,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 4))

        for r in resultats:
            couleur = Config.FG_SUN if r['type'] == 'solaire' else Config.FG_MOON
            date_str = r['date'].strftime("%d/%m/%Y %H:%M")
            self._ajouter_evt_ligne(date_str, r['details'], couleur)

    def _rechercher_conjonctions_gui(self):
        """Lance la recherche de conjonctions/oppositions et affiche les résultats."""
        self._vider_evt_scroll()
        try:
            s = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            dte = datetime.utcnow()

        ctk.CTkLabel(self.evt_scroll, text="Recherche en cours…",
                     text_color=Config.FG_LABEL).pack(pady=10)
        self.root.update_idletasks()
        self._vider_evt_scroll()

        resultats = MeeusEngine.rechercher_conjonctions(dte, nb_jours=365)

        if not resultats:
            ctk.CTkLabel(self.evt_scroll,
                         text="Aucun événement détecté sur 12 mois.",
                         text_color=Config.FG_LABEL).pack(pady=20)
            return

        ctk.CTkLabel(self.evt_scroll,
                     text=f"🪐  {len(resultats)} événement(s) trouvé(s) sur 12 mois",
                     text_color=Config.FG_WHITE,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 4))

        for r in resultats:
            if r['type'] == 'opposition':
                couleur = Config.FG_GREEN
            else:
                couleur = Config.FG_PURPLE
            date_str = r['date'].strftime("%d/%m/%Y")
            self._ajouter_evt_ligne(date_str, r['details'], couleur)

    def geolocaliser(self):
        """Détecte la position via ip-api.com et remplit lat/lon."""
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            if data["status"] == "success":
                self.entry_lat.delete(0, tk.END)
                self.entry_lat.insert(0, str(data["lat"]))
                self.entry_lon.delete(0, tk.END)
                self.entry_lon.insert(0, str(data["lon"]))
                messagebox.showinfo("Géolocalisation",
                    f"Lieu : {data['city']}, {data['country']}")
                self.calculer()
            else:
                messagebox.showerror("Erreur", "Position indéterminée.")
        except Exception as e:
            messagebox.showerror("Erreur réseau",
                "Vérifiez votre connexion.\nDétail : " + str(e))

    def toggle_live(self):
        """Active / désactive le mode temps réel."""
        self.live_mode = not self.live_mode
        if self.live_mode:
            self.btn_live.configure(fg_color=Config.FG_GREEN,
                text_color=Config.BG_MAIN, text="⏸ PAUSE")
            self.entry_date.configure(state="disabled")
            self.update_live()
        else:
            self.btn_live.configure(fg_color="transparent",
                text_color=Config.FG_WHITE, text="⏱ LIVE")
            self.entry_date.configure(state="normal")

    def update_live(self):
        """Callback récursif du mode temps réel (s'auto-planifie via root.after)."""
        if self.live_mode:
            now = datetime.utcnow()
            self.entry_date.configure(state="normal")
            self.entry_date.delete(0, tk.END)
            self.entry_date.insert(0, now.strftime("%d/%m/%Y %H:%M:%S"))
            self.entry_date.configure(state="disabled")
            self.calculer()
            self.root.after(_INTERVALLE_LIVE_MS, self.update_live)

    # ──────────────────────────────────────────────────────────────────
    # CALCUL PRINCIPAL
    # ──────────────────────────────────────────────────────────────────

    def calculer(self):
        """Lit les entrées, appelle MeeusEngine et met à jour toute l'interface."""
        try:
            s = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
            lat = float(self.entry_lat.get().replace(",", "."))
            lon = float(self.entry_lon.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erreur", "Format date ou coordonnées invalide.")
            return

        jd = MeeusEngine.jour_julien(dte)
        t  = MeeusEngine.siecle_julien2000(dte)

        s_l, _      = MeeusEngine.position_soleil(t)
        s_ra, s_dec = MeeusEngine.ecliptique_vers_equatorial(s_l, 0, t)
        s_alt, s_az = MeeusEngine.equatorial_vers_horizontal(jd, lat, lon, s_ra, s_dec)

        m_l, m_b, m_p = MeeusEngine.position_lune(t)
        m_ra, m_dec   = MeeusEngine.ecliptique_vers_equatorial(m_l, m_b, t)
        m_alt, m_az   = MeeusEngine.equatorial_vers_horizontal(jd, lat, lon, m_ra, m_dec)
        m_alt_c       = MeeusEngine.correction_elevation(m_alt, m_p)

        phase   = MeeusEngine.mod360(m_l - s_l)
        illum   = (1 - math.cos(math.radians(phase))) / 2.0 * 100.0

        self._soleil_data = {'nom': 'Soleil', 'ra': s_ra, 'dec': s_dec,
                             'alt': s_alt, 'az': s_az}
        self._lune_data = {'nom': 'Lune', 'ra': m_ra, 'dec': m_dec,
                           'alt': m_alt_c, 'az': m_az,
                           'illum': illum, 'phase': phase}

        # Cache événements journaliers
        key = f"{dte.strftime('%Y-%m-%d')}_{lat:.2f}_{lon:.2f}"
        redraw = key != self.last_cache_key
        if redraw:
            self.s_events = MeeusEngine.trouver_evenements(dte, lat, lon, "soleil")
            self.m_events = MeeusEngine.trouver_evenements(dte, lat, lon, "lune")
            self.last_cache_key = key

        eot = MeeusEngine.equation_du_temps(t)
        self.update_sun_card(s_ra, s_dec, s_alt, s_az, self.s_events, eot)
        self.update_moon_card(m_ra, m_dec, m_alt_c, m_az, illum, phase, self.m_events)
        self.tracer_graphiques(dte, lat, lon, s_alt, s_az, m_alt_c, m_az, redraw)
        self._calculer_planetes(dte, jd, t, lat, lon)
        self._update_status(lat, lon, dte)

    # ──────────────────────────────────────────────────────────────────
    # MISE À JOUR DES CARTES
    # ──────────────────────────────────────────────────────────────────

    def update_sun_card(self, ra, dec, alt, az, ev, eot=0.0):
        """Met à jour les labels Soleil et le badge d'état dans l'en-tête."""
        lb = self.sun_labels
        lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].configure(text=f"{alt:.2f}°")
        lb["Az"].configure(text=f"{az:.2f}°")
        lb["EoT"].configure(text=f"{eot:+.1f} min")

        lb["DawnAstro"].configure(text=self._fmt_event(ev["aube_astro"]))
        lb["DawnNaut"].configure(text=self._fmt_event(ev["aube_naut"]))
        lb["Dawn"].configure(text=self._fmt_event(ev["aube_civ"]))
        lb["Rise"].configure(text=self._fmt_event(ev["lever"]))
        lb["Transit"].configure(text=self._fmt_event(ev["culm"]))
        lb["Set"].configure(text=self._fmt_event(ev["coucher"]))
        lb["Dusk"].configure(text=self._fmt_event(ev["crep_civ"]))
        lb["DuskNaut"].configure(text=self._fmt_event(ev["crep_naut"]))
        lb["DuskAstro"].configure(text=self._fmt_event(ev["crep_astro"]))

        if alt > 0:
            self.lbl_sun_vis.configure(text="🌟 VISIBLE", text_color=Config.FG_GREEN)
        elif alt > -6:
            self.lbl_sun_vis.configure(text="🌅 CRÉP. CIVIL", text_color=Config.FG_SUN)
        elif alt > -12:
            self.lbl_sun_vis.configure(text="🌃 CRÉP. NAUT.", text_color=Config.BTN_COLOR)
        elif alt > -18:
            self.lbl_sun_vis.configure(text="🌌 CRÉP. ASTRO", text_color=Config.FG_PURPLE)
        else:
            self.lbl_sun_vis.configure(text="🌑 NUIT NOIRE", text_color=Config.FG_RED)

    def update_moon_card(self, ra, dec, alt, az, illum, phase, ev):
        """Met à jour les labels Lune et le badge d'état dans l'en-tête."""
        lb = self.moon_labels
        lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].configure(text=f"{alt:.2f}°")
        lb["Az"].configure(text=f"{az:.2f}°")
        lb["Illum"].configure(text=Formatters.phase_lune(illum, phase))
        lb["Rise"].configure(text=self._fmt_event(ev["lever"]))
        lb["Transit"].configure(text=self._fmt_event(ev["culm"]))
        lb["Set"].configure(text=self._fmt_event(ev["coucher"]))

        if alt > 0:
            self.lbl_moon_vis.configure(text="🌟 VISIBLE", text_color=Config.FG_GREEN)
        else:
            self.lbl_moon_vis.configure(text="🌑 COUCHÉE", text_color=Config.FG_RED)

    # ──────────────────────────────────────────────────────────────────
    # GRAPHIQUES
    # ──────────────────────────────────────────────────────────────────

    def tracer_graphiques(self, dte_ref, lat, lon, s_alt, s_az, m_alt, m_az, redraw_24h):
        """
        Met à jour les deux graphiques Matplotlib.

        ax1 (canvas1) : courbes d'altitude 24h — redessiné seulement si la date/lieu change.
        ax2 (canvas2) : carte polaire du ciel — redessiné à chaque appel.
        """
        # ── Graphique 24h ─────────────────────────────────────────────
        if redraw_24h:
            self.ax1.clear()

            # Recréer l'annotation (détruite par clear())
            self.annot = self.ax1.annotate("", xy=(0, 0), xytext=(15, 15),
                textcoords="offset points",
                bbox=dict(boxstyle="round4,pad=0.6", fc=Config.BG_PANEL,
                          ec=Config.FG_LABEL, lw=1),
                color="white", zorder=10, fontfamily="monospace")
            self.annot.set_visible(False)

            self.ax1.set_title(
                f"Trajectoire du {dte_ref.strftime('%d/%m/%Y')} (UT)",
                color=Config.FG_WHITE, pad=8, fontsize=11)
            for sp in self.ax1.spines.values():
                sp.set_color(Config.GRID_COLOR)

            self.heures, self.alt_soleil, self.alt_lune = [], [], []
            start = dte_ref.replace(hour=0, minute=0, second=0)
            for i in range(25):
                dt = start + timedelta(hours=i)
                jd = MeeusEngine.jour_julien(dt)
                t  = MeeusEngine.siecle_julien2000(dt)
                s_l, _ = MeeusEngine.position_soleil(t)
                h_s, _ = MeeusEngine.equatorial_vers_horizontal(
                    jd, lat, lon, *MeeusEngine.ecliptique_vers_equatorial(s_l, 0, t))
                m_l, m_b, m_p = MeeusEngine.position_lune(t)
                h_m, _ = MeeusEngine.equatorial_vers_horizontal(
                    jd, lat, lon, *MeeusEngine.ecliptique_vers_equatorial(m_l, m_b, t))
                self.heures.append(i)
                self.alt_soleil.append(h_s)
                self.alt_lune.append(MeeusEngine.correction_elevation(h_m, m_p))

            # ── Bandes de crépuscule verticales ───────────────────────
            # Conversion d'un événement solaire en heure décimale [0–24]
            def _h(cle):
                dt = self.s_events.get(cle)
                return None if dt is None else dt.hour + dt.minute / 60.0 + dt.second / 3600.0

            t_aa = _h('aube_astro');  t_an = _h('aube_naut')
            t_ac = _h('aube_civ');    t_lv = _h('lever')
            t_co = _h('coucher');     t_cc = _h('crep_civ')
            t_cn = _h('crep_naut');   t_ca = _h('crep_astro')

            # Palette nuit → crép. astro → naut → civil → jour (puis symétrique)
            _C_NUIT  = "#08081A"   # nuit noire
            _C_ASTRO = "#140F28"   # crép. astronomique
            _C_NAUT  = "#0E1E38"   # crép. nautique
            _C_CIVIL = "#2A1C10"   # crép. civil
            _C_JOUR  = "#1E1A0A"   # jour (fond légèrement chaud)

            def _vspan(x0, x1, color):
                if x0 is not None and x1 is not None and x0 < x1:
                    self.ax1.axvspan(x0, x1, color=color, alpha=1.0, zorder=0)

            # Séquence temporelle complète
            _vspan(0,    t_aa,  _C_NUIT)
            _vspan(t_aa, t_an,  _C_ASTRO)
            _vspan(t_an, t_ac,  _C_NAUT)
            _vspan(t_ac, t_lv,  _C_CIVIL)
            _vspan(t_lv, t_co,  _C_JOUR)
            _vspan(t_co, t_cc,  _C_CIVIL)
            _vspan(t_cc, t_cn,  _C_NAUT)
            _vspan(t_cn, t_ca,  _C_ASTRO)
            _vspan(t_ca, 24,    _C_NUIT)

            self.ax1.plot(self.heures, self.alt_soleil,
                          color=Config.FG_SUN, linewidth=2, label="Soleil")
            self.ax1.plot(self.heures, self.alt_lune,
                          color=Config.FG_MOON, linewidth=2, label="Lune")

            self.ax1.axhline(0,   color=Config.FG_RED,   linestyle="--", linewidth=1, alpha=0.7)
            self.ax1.axhline(-6,  color=Config.FG_SUN,   linestyle=":",  linewidth=0.7, alpha=0.4)
            self.ax1.axhline(-12, color=Config.BTN_COLOR, linestyle=":",  linewidth=0.7, alpha=0.4)
            self.ax1.axhline(-18, color=Config.FG_PURPLE, linestyle=":",  linewidth=0.7, alpha=0.4)

            self.ax1.set_xlim(0, 24)
            self.ax1.set_ylim(-90, 90)
            self.ax1.set_xticks(range(0, 25, 2))
            self.ax1.set_xlabel("Heure UT", color=Config.FG_LABEL, fontsize=9)
            self.ax1.set_ylabel("Altitude (°)", color=Config.FG_LABEL, fontsize=9)
            self.ax1.tick_params(colors=Config.FG_LABEL)
            self.ax1.grid(color=Config.GRID_COLOR, linestyle=":")
            self.ax1.legend(loc="upper right", facecolor=Config.BG_PANEL,
                            edgecolor=Config.GRID_COLOR, labelcolor=Config.FG_WHITE)
            self.canvas1.draw_idle()

        # ── Carte polaire ─────────────────────────────────────────────
        self.ax2.clear()
        self.ax2.set_title(
            f"Carte du Ciel  —  {dte_ref.strftime('%H:%M:%S')} UT",
            color=Config.FG_WHITE, pad=12, fontsize=11)
        self.ax2.spines["polar"].set_color(Config.GRID_COLOR)
        self.ax2.set_theta_zero_location("N")
        self.ax2.set_theta_direction(-1)
        self.ax2.set_xticks([math.radians(x) for x in range(0, 360, 45)])
        self.ax2.set_xticklabels(["N", "NE", "E", "SE", "S", "SO", "O", "NO"])
        self.ax2.set_ylim(0, 90)
        self.ax2.set_yticks([0, 30, 60, 90])
        self.ax2.set_yticklabels(["", "60°", "30°", "Horizon"],
                                  color=Config.FG_LABEL, fontsize=9)
        self.ax2.tick_params(colors=Config.FG_WHITE)
        self.ax2.grid(color=Config.GRID_COLOR, linestyle="-")

        # Étoiles
        jd = MeeusEngine.jour_julien(dte_ref)
        self.etoiles_visibles = []
        for nom, (ra_h, dec_d, mag) in _ETOILES.items():
            e_alt, e_az = MeeusEngine.equatorial_vers_horizontal(
                jd, lat, lon, ra_h, dec_d)
            if e_alt > 0:
                az_rad = math.radians(e_az)
                r      = 90 - e_alt
                taille = max(2, 10 - mag * 3.5)
                self.ax2.plot(az_rad, r, "o", color="#D8E8FF",
                              markersize=taille, alpha=0.85, zorder=2)
                if mag < 1.5:
                    self.ax2.annotate(nom, xy=(az_rad, r), xytext=(4, 4),
                        textcoords="offset points",
                        fontsize=7, color="#A0B8D8", zorder=3)
                self.etoiles_visibles.append((nom, mag, az_rad, r, e_alt, e_az))

        # ── Lignes de constellations ─────────────────────────────────
        pos_etoiles = {nom: (az_rad, r)
                       for nom, _, az_rad, r, _, _ in self.etoiles_visibles}
        for nom_const, aretes in CONSTELLATIONS.items():
            pts = []
            for ea, eb in aretes:
                if ea in pos_etoiles and eb in pos_etoiles:
                    az_a, r_a = pos_etoiles[ea]
                    az_b, r_b = pos_etoiles[eb]
                    self.ax2.plot([az_a, az_b], [r_a, r_b],
                                 color="#4A5568", linewidth=0.8,
                                 alpha=0.45, zorder=1)
                    pts.extend([(az_a, r_a), (az_b, r_b)])
            if len(pts) >= 4:
                xs = [r * math.cos(az) for az, r in pts]
                ys = [r * math.sin(az) for az, r in pts]
                cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
                c_az = math.atan2(cy, cx)
                c_r = math.hypot(cx, cy)
                self.ax2.annotate(nom_const, xy=(c_az, c_r),
                                  fontsize=6, color="#6B7280", alpha=0.7,
                                  ha="center", va="center", zorder=1)

        if s_alt > 0:
            self.ax2.plot(math.radians(s_az), 90 - s_alt, "o",
                          color=Config.FG_SUN, markersize=14, label="Soleil", zorder=5)
        if m_alt > 0:
            self.ax2.plot(math.radians(m_az), 90 - m_alt, "o",
                          color=Config.FG_MOON, markersize=12, label="Lune", zorder=5)

        n = len(self.etoiles_visibles)
        self.ax2.legend(
            handles=[
                plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=Config.FG_SUN, markersize=8,
                    label="Soleil", linewidth=0),
                plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=Config.FG_MOON, markersize=7,
                    label="Lune", linewidth=0),
                plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor="#D8E8FF", markersize=5,
                    label="Étoiles", linewidth=0),
            ],
            loc="upper right",
            facecolor=Config.BG_PANEL, edgecolor=Config.GRID_COLOR,
            labelcolor=Config.FG_WHITE, fontsize=8,
            title=f"{n} étoile{'s' if n != 1 else ''} visible{'s' if n != 1 else ''}",
            title_fontsize=7)

        self.canvas2.draw_idle()
