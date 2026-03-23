"""
gui.py — Graphical Interface and Controller for Céleste
=========================================================
v3.1 — New features:
  • Planets on sky map (diamond markers + labels + tooltip + click popup)
  • 🖨 EXPORT PDF button in sidebar
  • Enriched eclipses in Events tab:
      total/annular/hybrid type, diameter ratio, magnitude, duration

Architecture:
  - Left sidebar: parameters (date, location, timezone, favorites)
  - Main right area: tabs Ephemeris / Trajectories / Sky Map / Planets / Events
  - Bottom status bar: coordinates, visible stars/planets count, UT time

Dependencies:
    customtkinter, matplotlib, tkinter (stdlib)
    config.Config, utils.Formatters, engine.MeeusEngine, export_pdf
"""

import os
import tkinter as tk
from tkinter import messagebox, simpledialog
import tkinter.filedialog as fd
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
from constellations import STARS_EXTRA, CONSTELLATIONS, STAR_CONSTELLATION

# Live mode refresh interval (milliseconds)
_LIVE_UPDATE_INTERVAL_MS = 2000

# Favorites file path
_FAVORITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favorites.json")

# UTC offsets (-12 → +14)
_UTC_OFFSETS = [f"UTC{'+' if i >= 0 else ''}{i}" for i in range(-12, 15)]

# Star catalog: {name: (RA hours, Dec degrees, magnitude)}
_STARS = {
    "Sirius":      ( 6.7523, -16.7161, -1.46),
    "Arcturus":    (14.2612,  19.1822, -0.05),
    "Vega":        (18.6157,  38.7836,  0.03),
    "Capella":     ( 5.2782,  45.9980,  0.08),
    "Rigel":       ( 5.2423,  -8.2016,  0.13),
    "Procyon":     ( 7.6550,   5.2250,  0.34),
    "Betelgeuse":  ( 5.9194,   7.4070,  0.42),
    "Altair":      (19.8463,   8.8683,  0.77),
    "Aldebaran":   ( 4.5988,  16.5093,  0.87),
    "Spica":       (13.4199, -11.1613,  1.04),
    "Antares":     (16.4900, -26.4319,  1.06),
    "Pollux":      ( 7.7553,  28.0262,  1.16),
    "Fomalhaut":   (22.9608, -29.6223,  1.17),
    "Deneb":       (20.6905,  45.2803,  1.25),
    "Regulus":     (10.1395,  11.9672,  1.36),
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
    "Alhena":      ( 6.6285,  16.3992,  1.93),
    "Alphard":     ( 9.4597,  -8.6584,  1.99),
    "Hamal":       ( 2.1197,  23.4622,  2.01),
    "Denebola":    (11.8174,  14.5723,  2.14),
    "Merak":       (11.0307,  56.3824,  2.37),
    "Phecda":      (11.8966,  53.6948,  2.44),
    "Polaris":     ( 2.5303,  89.2641,  1.97),
}
_STARS.update(STARS_EXTRA)

# Planet style for sky map (diamond markers)
_PLANET_MAP_STYLE = {
    "Venus":   {"color": "#D4C060", "marker": "D", "size": 7,  "label": "Venus"},
    "Mars":    {"color": "#E07050", "marker": "D", "size": 7,  "label": "Mars"},
    "Jupiter": {"color": "#C8A870", "marker": "D", "size": 9,  "label": "Jupiter"},
    "Saturn":  {"color": "#C0C060", "marker": "D", "size": 8,  "label": "Saturn"},
}


class AstroApp:
    """Main Céleste application — View and MVC Controller."""

    def __init__(self, root):
        self.root = root
        self.root.title("Céleste — Astronomical Observatory")
        self.root.geometry("1280x800")
        self.root.minsize(1100, 700)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root.configure(bg=Config.BG_MAIN)

        # State
        self.live_mode    = False
        self.last_cache_key = ""
        self.sun_events   = {}
        self.moon_events  = {}
        self.hours        = []
        self.sun_altitudes  = []
        self.moon_altitudes = []
        self.utc_offset   = 0
        self.favorites    = self._load_favorites()
        self.visible_stars = []
        self.visible_planets_map = []   # planets on sky map
        self._sun_data    = {}
        self._moon_data   = {}
        self._detail_popup = None
        self.planet_labels = {}

        self.setup_ui()
        self.calculate()

    # ──────────────────────────────────────────────────────────────────
    # INTERFACE
    # ──────────────────────────────────────────────────────────────────

    def setup_ui(self):
        """Builds the interface: status bar + sidebar + main tabs."""

        # ── Status bar ────────────────────────────────────────────────
        sb = ctk.CTkFrame(self.root, fg_color=Config.BG_PANEL, corner_radius=0, height=24)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)

        self.lbl_status_position = ctk.CTkLabel(sb, text="📍 —",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_position.pack(side=tk.LEFT, padx=14)

        self.lbl_status_stars = ctk.CTkLabel(sb, text="",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_stars.pack(side=tk.LEFT, padx=10)

        self.lbl_status_time = ctk.CTkLabel(sb, text="UT : —",
            text_color=Config.FG_LABEL, font=("Consolas", 11))
        self.lbl_status_time.pack(side=tk.RIGHT, padx=14)

        # ── Left sidebar ──────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self.root, fg_color=Config.BG_MAIN,
                               corner_radius=0, width=290)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=8)
        sidebar.pack_propagate(False)

        # Logo header
        hdr = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 5))
        ctk.CTkLabel(hdr, text="✨ CÉLESTE", text_color=Config.FG_MOON,
                     font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT, padx=12, pady=8)
        ctk.CTkLabel(hdr, text="v3.1", text_color=Config.GRID_COLOR,
                     font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT, pady=(12, 0))
        self.btn_live = ctk.CTkButton(hdr, text="⏱ LIVE", command=self.toggle_live,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=76, font=("Segoe UI", 11))
        self.btn_live.pack(side=tk.RIGHT, padx=10)

        # Parameters section
        p = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        p.pack(fill=tk.X, padx=8, pady=5)
        ctk.CTkLabel(p, text="⚙  SETTINGS", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 10, "bold")).grid(
                     row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(8,5))

        ctk.CTkLabel(p, text="Date / Time UT :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=1, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_date = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_date.insert(0, datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        self.entry_date.grid(row=1, column=1, columnspan=2, pady=3, padx=(4,10), sticky=tk.EW)

        ctk.CTkLabel(p, text="Latitude :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=2, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_lat = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_lat.insert(0, "49.6333")
        self.entry_lat.grid(row=2, column=1, columnspan=2, pady=3, padx=(4,10), sticky=tk.EW)

        ctk.CTkLabel(p, text="Longitude :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=3, column=0, sticky=tk.W, padx=10, pady=3)
        self.entry_lon = ctk.CTkEntry(p, font=("Segoe UI", 11))
        self.entry_lon.insert(0, "-1.6167")
        self.entry_lon.grid(row=3, column=1, pady=3, padx=(4,4), sticky=tk.EW)
        ctk.CTkButton(p, text="📍", command=self.geolocate,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=32, font=("Segoe UI", 13)).grid(row=3, column=2, padx=(2,10))

        ctk.CTkLabel(p, text="Timezone :", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 11)).grid(row=4, column=0, sticky=tk.W, padx=10, pady=3)
        self.offset_menu = ctk.CTkOptionMenu(p, values=_UTC_OFFSETS,
            command=self._on_offset_change, font=("Segoe UI", 11))
        self.offset_menu.set("UTC+0")
        self.offset_menu.grid(row=4, column=1, columnspan=2, pady=3, padx=(4,10), sticky=tk.EW)
        p.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(p, text="⚡  CALCULATE", command=self.calculate,
            fg_color=Config.BTN_COLOR, text_color=Config.BG_MAIN,
            font=("Segoe UI", 12, "bold")).grid(
            row=5, column=0, columnspan=3, pady=(10,4), sticky=tk.EW, padx=10)

        # ── Export PDF button (NEW) ────────────────────────────────────
        ctk.CTkButton(p, text="🖨  EXPORT PDF", command=self.export_pdf,
            fg_color="transparent", border_color=Config.FG_MOON,
            border_width=1, font=("Segoe UI", 11)).grid(
            row=6, column=0, columnspan=3, pady=(0,8), sticky=tk.EW, padx=10)

        for w in (self.entry_date, self.entry_lat, self.entry_lon):
            w.bind("<Return>", lambda e: self.calculate())

        # Favorites section
        fav = ctk.CTkFrame(sidebar, fg_color=Config.BG_PANEL, corner_radius=8)
        fav.pack(fill=tk.X, padx=8, pady=5)
        ctk.CTkLabel(fav, text="📌  FAVORITE LOCATIONS", text_color=Config.FG_LABEL,
                     font=("Segoe UI", 10, "bold")).grid(
                     row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(8,5))
        names = list(self.favorites.keys())
        self.combo_favorites = ctk.CTkComboBox(fav,
            values=names if names else [""],
            command=self.apply_location, font=("Segoe UI", 11))
        self.combo_favorites.set("📍 Cherbourg-en-Cotentin")
        self.combo_favorites.grid(row=1, column=0, padx=(10,4), pady=(0,8), sticky=tk.EW)
        ctk.CTkButton(fav, text="💾", command=self.save_location,
            fg_color="transparent", border_color=Config.FG_WHITE,
            border_width=1, width=32, font=("Segoe UI", 13)).grid(row=1, column=1, padx=2)
        ctk.CTkButton(fav, text="🗑", command=self.delete_location,
            fg_color="transparent", border_color=Config.FG_RED, border_width=1,
            text_color=Config.FG_RED, width=32, font=("Segoe UI", 13)).grid(row=1, column=2, padx=(2,10))
        fav.grid_columnconfigure(0, weight=1)

        # ── Main content area ──────────────────────────────────────────
        content = ctk.CTkFrame(self.root, fg_color=Config.BG_MAIN, corner_radius=0)
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        tabs = ctk.CTkTabview(content,
            fg_color=Config.BG_PANEL,
            segmented_button_fg_color=Config.BG_MAIN,
            segmented_button_selected_color=Config.BTN_COLOR,
            segmented_button_selected_hover_color=Config.FG_MOON,
            anchor="nw")
        tabs.pack(fill=tk.BOTH, expand=True)

        # ── Tab 1: Ephemeris ───────────────────────────────────────────
        tab_eph = tabs.add("☀️🌙  Ephemeris")

        col_sun = ctk.CTkFrame(tab_eph, fg_color=Config.BG_MAIN, corner_radius=8)
        col_sun.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,3), pady=6)
        sun_hdr = ctk.CTkFrame(col_sun, fg_color="#2A2A1A", corner_radius=6)
        sun_hdr.pack(fill=tk.X, padx=6, pady=(6,0))
        ctk.CTkLabel(sun_hdr, text="  ☀️  SUN", font=("Segoe UI", 15, "bold"),
                     text_color=Config.FG_SUN).pack(side=tk.LEFT, padx=10, pady=8)
        self.lbl_sun_visible = ctk.CTkLabel(sun_hdr, text="",
            font=("Segoe UI", 11, "bold"), text_color=Config.FG_GREEN)
        self.lbl_sun_visible.pack(side=tk.RIGHT, padx=10)
        sun_data = ctk.CTkScrollableFrame(col_sun, fg_color="transparent")
        sun_data.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        sun_fields = [
            ("RA","Right Ascension"),("Dec","Declination"),("Alt","Altitude"),
            ("Az","Azimuth"),("EoT","Equation of Time"),
            ("DawnAstro","Astro. Dawn  −18°"),("DawnNaut","Naut. Dawn  −12°"),
            ("Dawn","Civil Dawn  −6°"),("Rise","Sunrise"),("Transit","Transit"),
            ("Set","Sunset"),("Dusk","Civil Dusk  −6°"),
            ("DuskNaut","Naut. Dusk −12°"),("DuskAstro","Astro. Dusk −18°"),
        ]
        self.sun_labels = self._build_data_grid(sun_data, Config.FG_SUN, sun_fields)

        ctk.CTkFrame(tab_eph, fg_color=Config.GRID_COLOR, width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=12)

        col_moon = ctk.CTkFrame(tab_eph, fg_color=Config.BG_MAIN, corner_radius=8)
        col_moon.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3,6), pady=6)
        moon_hdr = ctk.CTkFrame(col_moon, fg_color="#1A1A2A", corner_radius=6)
        moon_hdr.pack(fill=tk.X, padx=6, pady=(6,0))
        ctk.CTkLabel(moon_hdr, text="  🌙  MOON", font=("Segoe UI", 15, "bold"),
                     text_color=Config.FG_MOON).pack(side=tk.LEFT, padx=10, pady=8)
        self.lbl_moon_visible = ctk.CTkLabel(moon_hdr, text="",
            font=("Segoe UI", 11, "bold"), text_color=Config.FG_GREEN)
        self.lbl_moon_visible.pack(side=tk.RIGHT, padx=10)
        moon_data = ctk.CTkScrollableFrame(col_moon, fg_color="transparent")
        moon_data.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        moon_fields = [
            ("RA","Right Ascension"),("Dec","Declination"),("Alt","Altitude"),
            ("Az","Azimuth"),("Illum","Lunar Phase"),
            ("Rise","Moonrise"),("Transit","Transit"),("Set","Moonset"),
        ]
        self.moon_labels = self._build_data_grid(moon_data, Config.FG_MOON, moon_fields)

        # ── Tab 2: Trajectories ────────────────────────────────────────
        tab_traj = tabs.add("📈  Trajectories")
        self.fig1 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax1  = self.fig1.add_subplot(111, facecolor=Config.BG_PANEL)
        self.fig1.subplots_adjust(left=0.07, right=0.97, top=0.93, bottom=0.08)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=tab_traj)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.annot = self.ax1.annotate("", xy=(0,0), xytext=(15,15),
            textcoords="offset points",
            bbox=dict(boxstyle="round4,pad=0.6", fc=Config.BG_PANEL, ec=Config.FG_LABEL, lw=1),
            color="white", zorder=10, fontfamily="monospace")
        self.annot.set_visible(False)
        self.canvas1.mpl_connect("motion_notify_event", self.on_hover)

        # ── Tab 3: Sky Map ─────────────────────────────────────────────
        tab_map = tabs.add("🔭  Sky Map")
        self.fig2 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax2  = self.fig2.add_subplot(111, projection='polar', facecolor=Config.BG_PANEL)
        self.fig2.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.05)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=tab_map)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.annot2 = self.ax2.annotate("", xy=(0,0), xytext=(12,12),
            textcoords="offset points",
            bbox=dict(boxstyle="round4,pad=0.5", fc=Config.BG_PANEL, ec=Config.FG_MOON, lw=1),
            color="white", zorder=10, fontfamily="monospace", fontsize=8)
        self.annot2.set_visible(False)
        self.canvas2.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas2.mpl_connect("button_press_event", self._on_click_map)

        # ── Tab 4: Planets ─────────────────────────────────────────────
        tab_pl = tabs.add("🪐  Planets")
        left_pl = ctk.CTkFrame(tab_pl, fg_color=Config.BG_MAIN, corner_radius=0)
        left_pl.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(4,2), pady=4)
        left_pl.configure(width=310); left_pl.pack_propagate(False)

        _PLANETS_CFG = [
            ("Venus",   "♀  VENUS",   "#D4C060", "#28271A"),
            ("Mars",    "♂  MARS",    "#E07050", "#2A1A18"),
            ("Jupiter", "♃  JUPITER", "#C8A870", "#28231A"),
            ("Saturn",  "♄  SATURN",  "#C0C060", "#23251A"),
        ]
        self.planet_labels = {}
        pl_fields = [("RA","Right Ascension"),("Dec","Declination"),
                     ("Alt","Altitude"),("Az","Azimuth"),("Dist","Distance (AU)")]
        for pname, ptitle, pcolor, pbg in _PLANETS_CFG:
            card = ctk.CTkFrame(left_pl, fg_color=Config.BG_PANEL, corner_radius=8)
            card.pack(fill=tk.X, padx=6, pady=4)
            phdr = ctk.CTkFrame(card, fg_color=pbg, corner_radius=6)
            phdr.pack(fill=tk.X)
            ctk.CTkLabel(phdr, text=f"  {ptitle}",
                font=("Segoe UI", 13, "bold"), text_color=pcolor).pack(side=tk.LEFT, padx=8, pady=5)
            vis_lbl = ctk.CTkLabel(phdr, text="",
                font=("Segoe UI", 10, "bold"), text_color=Config.FG_GREEN)
            vis_lbl.pack(side=tk.RIGHT, padx=8)
            data_frame = ctk.CTkFrame(card, fg_color="transparent")
            data_frame.pack(fill=tk.X, padx=2, pady=2)
            lbls = self._build_data_grid(data_frame, pcolor, pl_fields)
            lbls["_vis"] = vis_lbl
            self.planet_labels[pname] = lbls

        right_pl = ctk.CTkFrame(tab_pl, fg_color=Config.BG_MAIN, corner_radius=0)
        right_pl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2,4), pady=4)
        self.fig3 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax3  = self.fig3.add_subplot(111, aspect='equal', facecolor=Config.BG_PANEL)
        self.fig3.subplots_adjust(left=0.05, right=0.97, top=0.93, bottom=0.05)
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=right_pl)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ── Tab 5: Events ──────────────────────────────────────────────
        tab_evt = tabs.add("📅  Events")
        btn_frame = ctk.CTkFrame(tab_evt, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=10, pady=(10,4))
        ctk.CTkButton(btn_frame, text="🔍  Search Eclipses (12 months)",
                      command=self._search_eclipses_gui,
                      fg_color=Config.BTN_COLOR, height=32,
                      font=ctk.CTkFont(size=12)).pack(side=tk.LEFT, padx=(0,8))
        ctk.CTkButton(btn_frame, text="🔍  Search Conjunctions (12 months)",
                      command=self._search_conjunctions_gui,
                      fg_color=Config.FG_PURPLE, height=32,
                      font=ctk.CTkFont(size=12)).pack(side=tk.LEFT)
        self.evt_scroll = ctk.CTkScrollableFrame(tab_evt, fg_color=Config.BG_MAIN, corner_radius=8)
        self.evt_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4,10))
        ctk.CTkLabel(self.evt_scroll, text="Click a button to launch search.",
                     text_color=Config.FG_LABEL, font=ctk.CTkFont(size=11)).pack(pady=20)

    def _build_data_grid(self, parent, color, fields):
        TIME_KEYS = {"Rise","Transit","Set","Dawn","Dusk","Illum",
                     "DawnNaut","DuskNaut","DawnAstro","DuskAstro"}
        labels = {}
        row_colors = [Config.BG_PANEL, Config.BG_MAIN]
        for i, (key, text) in enumerate(fields):
            row = ctk.CTkFrame(parent, fg_color=row_colors[i%2], corner_radius=4)
            row.pack(fill=tk.X, pady=1, padx=2)
            ctk.CTkLabel(row, text=text, text_color=Config.FG_LABEL,
                         font=("Segoe UI", 11), anchor="w",
                         width=150).pack(side=tk.LEFT, padx=(10,4), pady=4)
            val_color = Config.FG_WHITE if key in TIME_KEYS else color
            lbl = ctk.CTkLabel(row, text="—", text_color=val_color,
                               font=("Consolas", 11, "bold"), anchor="e")
            lbl.pack(side=tk.RIGHT, padx=10, pady=4)
            labels[key] = lbl
        return labels

    # ──────────────────────────────────────────────────────────────────
    # EXPORT PDF (NEW)
    # ──────────────────────────────────────────────────────────────────

    def export_pdf(self):
        """Generates ephemeris PDF report and prompts for save location."""
        try:
            from export_pdf import generate_report_pdf, build_data_from_app
        except ImportError:
            messagebox.showerror("Export PDF",
                "Module export_pdf.py not found.\n"
                "Place export_pdf.py in the same folder as gui.py.")
            return

        ts   = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        path = fd.asksaveasfilename(
            title="Save PDF report",
            defaultextension=".pdf",
            filetypes=[("PDF file", "*.pdf")],
            initialfile=f"celeste_{ts}.pdf",
        )
        if not path:
            return
        try:
            data = build_data_from_app(self)
            generate_report_pdf(data, path)
            messagebox.showinfo("Export PDF", f"Report saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Export PDF error", str(e))

    # ──────────────────────────────────────────────────────────────────
    # PLANETS
    # ──────────────────────────────────────────────────────────────────

    def _calculate_planets(self, dte, jd, t, lat, lon):
        if not self.planet_labels:
            return
        from engine import _ORBITAL_ELEMENTS
        helio = {}
        for pname, lb in self.planet_labels.items():
            ra, dec, dist = MeeusEngine.planet_position(t, pname)
            p_alt, p_az  = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, ra, dec)
            lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
            lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
            lb["Alt"].configure(text=f"{p_alt:.2f}°")
            lb["Az"].configure(text=f"{p_az:.2f}°")
            lb["Dist"].configure(text=f"{dist:.4f} AU")
            if p_alt > 0:
                lb["_vis"].configure(text="🌟 VISIBLE", text_color=Config.FG_GREEN)
            else:
                lb["_vis"].configure(text="⬇ BELOW HORIZON", text_color=Config.FG_RED)
            L0, L1, a, *_ = _ORBITAL_ELEMENTS[pname]
            helio[pname] = (a, math.radians(MeeusEngine.mod360(L0 + L1*t)))
        self._plot_orrery(t, helio)

    def _plot_orrery(self, t, helio):
        ax = self.ax3
        ax.clear(); ax.set_facecolor(Config.BG_PANEL)
        ax.set_title("Solar System — Top-down View (J2000.0)", color=Config.FG_WHITE, fontsize=10, pad=8)
        ax.tick_params(colors=Config.FG_LABEL, labelsize=8)
        for sp in ax.spines.values(): sp.set_color(Config.GRID_COLOR)
        ax.grid(color=Config.GRID_COLOR, linestyle=":", alpha=0.4)
        ax.plot(0, 0, "o", color=Config.FG_SUN, markersize=14, zorder=5)
        ax.annotate("Sun", xy=(0,0), xytext=(0.18,0.05), color=Config.FG_SUN, fontsize=8)
        s_l, r_e = MeeusEngine.sun_position(t)
        l_e = math.radians(MeeusEngine.mod360(s_l + 180))
        xe, ye = r_e*math.cos(l_e), r_e*math.sin(l_e)
        theta = [i*math.tau/360 for i in range(361)]
        ax.plot([r_e*math.cos(a) for a in theta],[r_e*math.sin(a) for a in theta],
                color=Config.FG_MOON, linewidth=0.5, alpha=0.3)
        ax.plot(xe, ye, "o", color=Config.FG_MOON, markersize=7, zorder=5)
        ax.annotate("Earth", xy=(xe,ye), xytext=(xe+0.1,ye+0.1), color=Config.FG_MOON, fontsize=8)
        _PC = {"Venus":"#D4C060","Mars":"#E07050","Jupiter":"#C8A870","Saturn":"#C0C060"}
        _PS = {"Venus":6,"Mars":6,"Jupiter":9,"Saturn":8}
        for pname,(a,l_rad) in helio.items():
            xp,yp = a*math.cos(l_rad),a*math.sin(l_rad)
            color = _PC[pname]
            ax.plot([a*math.cos(ang) for ang in theta],[a*math.sin(ang) for ang in theta],
                    color=color, linewidth=0.5, alpha=0.25)
            ax.plot(xp,yp,"o",color=color,markersize=_PS[pname],zorder=4)
            ax.annotate(pname,xy=(xp,yp),xytext=(xp+0.1,yp+0.15),color=color,fontsize=8)
        limit = 11.0
        ax.set_xlim(-limit,limit); ax.set_ylim(-limit,limit)
        ax.set_xlabel("AU", color=Config.FG_LABEL, fontsize=8)
        ax.set_ylabel("AU", color=Config.FG_LABEL, fontsize=8)
        self.canvas3.draw_idle()

    # ──────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────

    def _update_status(self, lat, lon, dte):
        self.lbl_status_position.configure(text=f"📍 Lat: {lat:+.4f}°  Lon: {lon:+.4f}°")
        n      = len(self.visible_stars)
        np_vis = len(self.visible_planets_map)
        extra  = f"  ♦ {np_vis} planet{'s' if np_vis != 1 else ''}" if np_vis else ""
        self.lbl_status_stars.configure(
            text=f"★ {n} star{'s' if n != 1 else ''} visible{extra}")
        self.lbl_status_time.configure(
            text=f"UT : {dte.strftime('%d/%m/%Y  %H:%M:%S')}")

    # ──────────────────────────────────────────────────────────────────
    # FAVORITES
    # ──────────────────────────────────────────────────────────────────

    def _load_favorites(self):
        if os.path.exists(_FAVORITES_FILE):
            with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_favorites(self):
        with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def _refresh_combo_favorites(self):
        names = list(self.favorites.keys())
        self.combo_favorites.configure(values=names if names else [""])

    def save_location(self):
        try:
            lat = float(self.entry_lat.get().replace(",", "."))
            lon = float(self.entry_lon.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "Invalid coordinates."); return
        name = simpledialog.askstring("Save Location", "Name:", parent=self.root)
        if name and name.strip():
            name = name.strip()
            self.favorites[name] = {"lat": lat, "lon": lon}
            self._save_favorites(); self._refresh_combo_favorites()
            self.combo_favorites.set(name)

    def delete_location(self):
        name = self.combo_favorites.get()
        if name in self.favorites:
            del self.favorites[name]
            self._save_favorites(); self._refresh_combo_favorites()
            self.combo_favorites.set("")

    def apply_location(self, choice):
        if choice in self.favorites:
            loc = self.favorites[choice]
            self.entry_lat.delete(0, tk.END); self.entry_lat.insert(0, str(loc["lat"]))
            self.entry_lon.delete(0, tk.END); self.entry_lon.insert(0, str(loc["lon"]))
            self.calculate()

    # ──────────────────────────────────────────────────────────────────
    # TIMEZONE
    # ──────────────────────────────────────────────────────────────────

    def _on_offset_change(self, choice):
        val = choice.replace("UTC","").replace("+","")
        self.utc_offset = int(val)
        self.calculate()

    def _format_event(self, dt):
        if dt is None: return "--:--"
        return (dt + timedelta(hours=self.utc_offset)).strftime("%H:%M")

    # ──────────────────────────────────────────────────────────────────
    # HOVER TOOLTIP
    # ──────────────────────────────────────────────────────────────────

    def on_hover(self, event):
        c1, c2 = False, False

        if event.inaxes == self.ax1:
            x = event.xdata
            if x is not None and self.hours:
                idx = min(range(len(self.hours)), key=lambda i: abs(self.hours[i]-x))
                h = self.hours[idx]
                a_s, a_m = self.sun_altitudes[idx], self.moon_altitudes[idx]
                self.annot.xy = (h, max(a_s,a_m))
                self.annot.set_text(
                    f"UT : {h:02d}h00\nSun  : {a_s:+.1f}°\nMoon : {a_m:+.1f}°")
                self.annot.set_visible(True); c1 = True
            if self.annot2.get_visible():
                self.annot2.set_visible(False); c2 = True

        elif event.inaxes == self.ax2:
            if event.xdata is not None:
                xm = event.ydata * math.cos(event.xdata)
                ym = event.ydata * math.sin(event.xdata)
                best, bd, best_type = None, float('inf'), "star"

                for item in self.visible_stars:
                    _, _, az, r, _, _ = item
                    d = math.hypot(xm - r*math.cos(az), ym - r*math.sin(az))
                    if d < bd: bd, best, best_type = d, item, "star"

                for pl in self.visible_planets_map:
                    d = math.hypot(xm - pl['r']*math.cos(pl['az']),
                                   ym - pl['r']*math.sin(pl['az']))
                    if d < bd: bd, best, best_type = d, pl, "planet"

                if bd < 7 and best:
                    if best_type == "star":
                        name, mag, az, r, alt, azd = best
                        self.annot2.xy = (az, r)
                        self.annot2.set_text(
                            f"★ {name}\nAlt : {alt:.1f}°  Az : {azd:.1f}°\nMag : {mag:+.2f}")
                    else:
                        self.annot2.xy = (best['az'], best['r'])
                        self.annot2.set_text(
                            f"♦ {best['label']}\n"
                            f"Alt : {best['alt']:.1f}°  Az : {best['az_deg']:.1f}°\n"
                            f"Dist: {best['dist']:.3f} AU")
                    self.annot2.set_visible(True); c2 = True
                elif self.annot2.get_visible():
                    self.annot2.set_visible(False); c2 = True
            if self.annot.get_visible():
                self.annot.set_visible(False); c1 = True

        else:
            if self.annot.get_visible():  self.annot.set_visible(False);  c1 = True
            if self.annot2.get_visible(): self.annot2.set_visible(False); c2 = True

        if c1: self.canvas1.draw_idle()
        if c2: self.canvas2.draw_idle()

    # ──────────────────────────────────────────────────────────────────
    # CLICK ON MAP
    # ──────────────────────────────────────────────────────────────────

    def _on_click_map(self, event):
        if event.inaxes != self.ax2 or event.xdata is None:
            return
        xm = event.ydata * math.cos(event.xdata)
        ym = event.ydata * math.sin(event.xdata)
        best, bd, best_type = None, float('inf'), "star"

        for item in self.visible_stars:
            _, _, az, r, _, _ = item
            d = math.hypot(xm - r*math.cos(az), ym - r*math.sin(az))
            if d < bd: bd, best, best_type = d, item, "star"

        for obj in (self._sun_data, self._moon_data):
            if obj and obj.get('alt', -90) > 0:
                az_r = math.radians(obj['az']); r = 90 - obj['alt']
                d = math.hypot(xm - r*math.cos(az_r), ym - r*math.sin(az_r))
                if d < bd: bd, best, best_type = d, obj, "body"

        for pl in self.visible_planets_map:
            d = math.hypot(xm - pl['r']*math.cos(pl['az']),
                           ym - pl['r']*math.sin(pl['az']))
            if d < bd: bd, best, best_type = d, pl, "planet"

        if bd > 10:
            return

        if best_type == "star" and isinstance(best, tuple):
            name, mag, _, _, alt, azd = best
            ra_h, dec_d, _ = _STARS[name]
            consts = STAR_CONSTELLATION.get(name, [])
            self._show_object_detail(name=name, icon="★", ra=ra_h, dec=dec_d,
                alt=alt, az=azd, mag=mag,
                constellation=", ".join(consts) if consts else "—")
        elif best_type == "body" and isinstance(best, dict):
            icon = "☀" if best['name'] == "Sun" else "☾"
            self._show_object_detail(name=best['name'], icon=icon,
                ra=best.get('ra'), dec=best.get('dec'),
                alt=best['alt'], az=best['az'], mag=None, constellation=None, extra=best)
        elif best_type == "planet" and isinstance(best, dict):
            self._show_object_detail(name=best['label'], icon="♦",
                ra=best['ra'], dec=best['dec'],
                alt=best['alt'], az=best['az_deg'], mag=None, constellation=None,
                extra={'dist_au': best['dist']})

    def _show_object_detail(self, name, icon, ra, dec, alt, az, mag,
                             constellation, extra=None):
        if self._detail_popup is not None:
            try: self._detail_popup.destroy()
            except Exception: pass

        popup = ctk.CTkToplevel(self.root)
        popup.title(f"Details — {name}")
        popup.geometry("320x320")
        popup.configure(fg_color=Config.BG_PANEL)
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        self._detail_popup = popup

        ctk.CTkLabel(popup, text=f"{icon}  {name}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=Config.FG_WHITE).pack(pady=(12,4))
        frame = ctk.CTkFrame(popup, fg_color=Config.BG_MAIN, corner_radius=8)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        infos = []
        if constellation:   infos.append(("Constellation", constellation))
        if ra is not None:  infos.append(("Right Ascension", Formatters.hms(ra)))
        if dec is not None: infos.append(("Declination", Formatters.dms(dec)))
        infos.append(("Altitude", f"{alt:+.2f}°"))
        infos.append(("Azimuth",  f"{az:.2f}°"))
        if mag is not None: infos.append(("Magnitude", f"{mag:+.2f}"))
        if alt > 0:         infos.append(("Visibility", "Above horizon"))
        if extra and 'illum' in extra:
            infos.append(("Illumination", f"{extra['illum']:.1f} %"))
            infos.append(("Phase", Formatters.lunar_phase(extra['illum'], extra['phase'])))
        if extra and 'dist_au' in extra:
            infos.append(("Distance", f"{extra['dist_au']:.4f} AU"))

        for label, value in infos:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill=tk.X, padx=8, pady=2)
            ctk.CTkLabel(row, text=f"{label} :", text_color=Config.FG_LABEL,
                         font=ctk.CTkFont(size=11), anchor="w", width=120).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=str(value), text_color=Config.FG_WHITE,
                         font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side=tk.LEFT)

        ctk.CTkButton(popup, text="Close", command=popup.destroy,
                      fg_color=Config.BTN_COLOR, width=100, height=28).pack(pady=(4,10))

    # ──────────────────────────────────────────────────────────────────
    # EVENTS TAB
    # ──────────────────────────────────────────────────────────────────

    def _clear_evt_scroll(self):
        for w in self.evt_scroll.winfo_children(): w.destroy()

    def _add_evt_line(self, date_str, text, color):
        row = ctk.CTkFrame(self.evt_scroll, fg_color=Config.BG_PANEL, corner_radius=6)
        row.pack(fill=tk.X, pady=2, padx=4)
        ctk.CTkLabel(row, text=date_str, text_color=Config.FG_WHITE,
                     font=ctk.CTkFont(size=11, weight="bold"), width=140,
                     anchor="w").pack(side=tk.LEFT, padx=(10,6), pady=6)
        ctk.CTkLabel(row, text=text, text_color=color,
                     font=ctk.CTkFont(size=11), anchor="w").pack(
                         side=tk.LEFT, padx=(0,10), pady=6)

    def _search_eclipses_gui(self):
        """Launches HP eclipse search and displays enriched results."""
        self._clear_evt_scroll()
        try:
            s   = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            dte = datetime.utcnow()

        ctk.CTkLabel(self.evt_scroll,
                     text="Searching… (VSOP87 + ELP2000)",
                     text_color=Config.FG_LABEL).pack(pady=10)
        self.root.update_idletasks()
        self._clear_evt_scroll()

        results = MeeusEngine.find_eclipses(dte, num_months=12)

        if not results:
            ctk.CTkLabel(self.evt_scroll, text="No eclipses detected over 12 months.",
                         text_color=Config.FG_LABEL).pack(pady=20)
            return

        nb_sol = sum(1 for r in results if r['type'] == 'solar')
        nb_lun = sum(1 for r in results if r['type'] == 'lunar')
        ctk.CTkLabel(
            self.evt_scroll,
            text=(f"🌑  {len(results)} eclipse(s) — "
                  f"{nb_sol} solar  |  {nb_lun} lunar  "
                  f"[VSOP87 + ELP2000]"),
            text_color=Config.FG_WHITE,
            font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8,4))

        _COLORS = {'total': Config.FG_SUN, 'annular': Config.FG_PURPLE,
                   'hybrid': Config.FG_GREEN, 'partial': Config.FG_LABEL}
        _EMOJI  = {'total': '🌑', 'annular': '⭕', 'hybrid': '🔄', 'partial': '🌘'}

        for r in results:
            date_str = r['date'].strftime("%d/%m/%Y  %H:%M")

            if r['type'] == 'solar':
                sub   = r.get('sub_type', '---')
                ratio = r.get('diameter_ratio')
                mag   = r.get('magnitude')
                dur   = r.get('duration_min')
                cert  = r.get('certainty', '---')
                color = _COLORS.get(sub, Config.FG_LABEL)
                emoji = _EMOJI.get(sub, '🌘')

                self._add_evt_line(date_str,
                    f"{emoji}  Solar eclipse {sub.upper()}  ({cert})", color)

                detail_frame = ctk.CTkFrame(self.evt_scroll,
                    fg_color=Config.BG_MAIN, corner_radius=4)
                detail_frame.pack(fill=tk.X, pady=(0,6), padx=(24,4))

                details = []
                if ratio is not None:
                    sens = "(Moon > Sun)" if ratio > 1 else "(Moon < Sun)"
                    details.append(f"  Diameter ratio Moon/Sun : {ratio:.4f}  {sens}")
                if mag is not None:
                    details.append(f"  Magnitude                : {mag:.3f}")
                if dur is not None and sub in ('total','annular','hybrid'):
                    m_ = int(dur); s_ = int((dur-m_)*60)
                    details.append(f"  Central phase duration   : ~{m_}min {s_:02d}s")
                elif sub == 'partial':
                    details.append("  Central phase duration   : — (partial)")
                details.append(f"  Moon lat at syzygy       : {r['moon_latitude']:+.3f}°")

                for d in details:
                    ctk.CTkLabel(detail_frame, text=d, text_color=Config.FG_LABEL,
                                 font=ctk.CTkFont(size=10), anchor="w").pack(
                                     fill=tk.X, padx=8, pady=1)
            else:
                cert = r.get('certainty','---')
                self._add_evt_line(date_str,
                    f"🌕  Lunar eclipse  ({cert})"
                    f"  — Moon lat: {r['moon_latitude']:+.2f}°",
                    Config.FG_MOON)

    def _search_conjunctions_gui(self):
        self._clear_evt_scroll()
        try:
            s   = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            dte = datetime.utcnow()

        ctk.CTkLabel(self.evt_scroll, text="Searching…",
                     text_color=Config.FG_LABEL).pack(pady=10)
        self.root.update_idletasks()
        self._clear_evt_scroll()

        results = MeeusEngine.find_conjunctions(dte, num_days=365)

        if not results:
            ctk.CTkLabel(self.evt_scroll, text="No events detected over 12 months.",
                         text_color=Config.FG_LABEL).pack(pady=20)
            return

        ctk.CTkLabel(self.evt_scroll,
                     text=f"🪐  {len(results)} event(s) found over 12 months",
                     text_color=Config.FG_WHITE,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8,4))

        for r in results:
            color    = Config.FG_GREEN if r['type'] == 'opposition' else Config.FG_PURPLE
            date_str = r['date'].strftime("%d/%m/%Y")
            self._add_evt_line(date_str, r['details'], color)

    # ──────────────────────────────────────────────────────────────────
    # GEOLOCATE / LIVE
    # ──────────────────────────────────────────────────────────────────

    def geolocate(self):
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            if data["status"] == "success":
                self.entry_lat.delete(0, tk.END); self.entry_lat.insert(0, str(data["lat"]))
                self.entry_lon.delete(0, tk.END); self.entry_lon.insert(0, str(data["lon"]))
                messagebox.showinfo("Geolocation",
                    f"Location: {data['city']}, {data['country']}")
                self.calculate()
            else:
                messagebox.showerror("Error", "Position undetermined.")
        except Exception as e:
            messagebox.showerror("Network Error", "Check your connection.\nDetails: " + str(e))

    def toggle_live(self):
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
        if self.live_mode:
            now = datetime.utcnow()
            self.entry_date.configure(state="normal")
            self.entry_date.delete(0, tk.END)
            self.entry_date.insert(0, now.strftime("%d/%m/%Y %H:%M:%S"))
            self.entry_date.configure(state="disabled")
            self.calculate()
            self.root.after(_LIVE_UPDATE_INTERVAL_MS, self.update_live)

    # ──────────────────────────────────────────────────────────────────
    # MAIN CALCULATION
    # ──────────────────────────────────────────────────────────────────

    def calculate(self):
        try:
            s   = self.entry_date.get()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
            lat = float(self.entry_lat.get().replace(",","."))
            lon = float(self.entry_lon.get().replace(",","."))
        except ValueError:
            messagebox.showerror("Error","Invalid date format or coordinates."); return

        jd = MeeusEngine.julian_day(dte)
        t  = MeeusEngine.julian_century_j2000(dte)

        s_l, _       = MeeusEngine.sun_position(t)
        s_ra, s_dec  = MeeusEngine.ecliptic_to_equatorial(s_l, 0, t)
        s_alt, s_az  = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, s_ra, s_dec)

        m_l, m_b, m_p  = MeeusEngine.moon_position(t)
        m_ra, m_dec    = MeeusEngine.ecliptic_to_equatorial(m_l, m_b, t)
        m_alt, m_az    = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, m_ra, m_dec)
        m_alt_c        = MeeusEngine.elevation_correction(m_alt, m_p)

        phase = MeeusEngine.mod360(m_l - s_l)
        illum = (1 - math.cos(math.radians(phase))) / 2.0 * 100.0

        self._sun_data  = {'name': 'Sun',  'ra': s_ra, 'dec': s_dec, 'alt': s_alt, 'az': s_az}
        self._moon_data = {'name': 'Moon', 'ra': m_ra, 'dec': m_dec,
                           'alt': m_alt_c, 'az': m_az, 'illum': illum, 'phase': phase}

        key    = f"{dte.strftime('%Y-%m-%d')}_{lat:.2f}_{lon:.2f}"
        redraw = key != self.last_cache_key
        if redraw:
            self.sun_events  = MeeusEngine.find_events(dte, lat, lon, "sun")
            self.moon_events = MeeusEngine.find_events(dte, lat, lon, "moon")
            self.last_cache_key = key

        eot = MeeusEngine.equation_of_time(t)
        self.update_sun_card(s_ra, s_dec, s_alt, s_az, self.sun_events, eot)
        self.update_moon_card(m_ra, m_dec, m_alt_c, m_az, illum, phase, self.moon_events)
        self.plot_graphs(dte, lat, lon, s_alt, s_az, m_alt_c, m_az, redraw)
        self._calculate_planets(dte, jd, t, lat, lon)
        self._update_status(lat, lon, dte)

    # ──────────────────────────────────────────────────────────────────
    # CARD UPDATES
    # ──────────────────────────────────────────────────────────────────

    def update_sun_card(self, ra, dec, alt, az, ev, eot=0.0):
        lb = self.sun_labels
        lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].configure(text=f"{alt:.2f}°")
        lb["Az"].configure(text=f"{az:.2f}°")
        lb["EoT"].configure(text=f"{eot:+.1f} min")
        lb["DawnAstro"].configure(text=self._format_event(ev["dawn_astro"]))
        lb["DawnNaut"].configure(text=self._format_event(ev["dawn_naut"]))
        lb["Dawn"].configure(text=self._format_event(ev["dawn_civ"]))
        lb["Rise"].configure(text=self._format_event(ev["rise"]))
        lb["Transit"].configure(text=self._format_event(ev["transit"]))
        lb["Set"].configure(text=self._format_event(ev["set"]))
        lb["Dusk"].configure(text=self._format_event(ev["dusk_civ"]))
        lb["DuskNaut"].configure(text=self._format_event(ev["dusk_naut"]))
        lb["DuskAstro"].configure(text=self._format_event(ev["dusk_astro"]))

        if alt > 0:        self.lbl_sun_visible.configure(text="🌟 VISIBLE",            text_color=Config.FG_GREEN)
        elif alt > -6:     self.lbl_sun_visible.configure(text="🌅 CIVIL TWILIGHT",     text_color=Config.FG_SUN)
        elif alt > -12:    self.lbl_sun_visible.configure(text="🌃 NAUTICAL TWILIGHT",  text_color=Config.BTN_COLOR)
        elif alt > -18:    self.lbl_sun_visible.configure(text="🌌 ASTRO. TWILIGHT",    text_color=Config.FG_PURPLE)
        else:              self.lbl_sun_visible.configure(text="🌑 PITCH DARK",         text_color=Config.FG_RED)

    def update_moon_card(self, ra, dec, alt, az, illum, phase, ev):
        lb = self.moon_labels
        lb["RA"].configure(text=f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].configure(text=f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].configure(text=f"{alt:.2f}°")
        lb["Az"].configure(text=f"{az:.2f}°")
        lb["Illum"].configure(text=Formatters.lunar_phase(illum, phase))
        lb["Rise"].configure(text=self._format_event(ev["rise"]))
        lb["Transit"].configure(text=self._format_event(ev["transit"]))
        lb["Set"].configure(text=self._format_event(ev["set"]))
        if alt > 0: self.lbl_moon_visible.configure(text="🌟 VISIBLE",        text_color=Config.FG_GREEN)
        else:       self.lbl_moon_visible.configure(text="🌑 BELOW HORIZON",  text_color=Config.FG_RED)

    # ──────────────────────────────────────────────────────────────────
    # GRAPHS
    # ──────────────────────────────────────────────────────────────────

    def plot_graphs(self, dte_ref, lat, lon, s_alt, s_az, m_alt, m_az, redraw_24h):

        # ── 24h trajectory graph ──────────────────────────────────────
        if redraw_24h:
            self.ax1.clear()
            self.annot = self.ax1.annotate("", xy=(0,0), xytext=(15,15),
                textcoords="offset points",
                bbox=dict(boxstyle="round4,pad=0.6", fc=Config.BG_PANEL,
                          ec=Config.FG_LABEL, lw=1),
                color="white", zorder=10, fontfamily="monospace")
            self.annot.set_visible(False)

            self.ax1.set_title(
                f"Altitude Trajectory for {dte_ref.strftime('%d/%m/%Y')} (UT)",
                color=Config.FG_WHITE, pad=8, fontsize=11)
            for sp in self.ax1.spines.values():
                sp.set_color(Config.GRID_COLOR)

            self.hours, self.sun_altitudes, self.moon_altitudes = [], [], []
            start = dte_ref.replace(hour=0, minute=0, second=0)
            for i in range(25):
                dt  = start + timedelta(hours=i)
                jd  = MeeusEngine.julian_day(dt)
                t   = MeeusEngine.julian_century_j2000(dt)
                s_l, _ = MeeusEngine.sun_position(t)
                h_s, _ = MeeusEngine.equatorial_to_horizontal(
                    jd, lat, lon, *MeeusEngine.ecliptic_to_equatorial(s_l, 0, t))
                m_l, m_b, m_p = MeeusEngine.moon_position(t)
                h_m, _ = MeeusEngine.equatorial_to_horizontal(
                    jd, lat, lon, *MeeusEngine.ecliptic_to_equatorial(m_l, m_b, t))
                self.hours.append(i)
                self.sun_altitudes.append(h_s)
                self.moon_altitudes.append(MeeusEngine.elevation_correction(h_m, m_p))

            def _h(key):
                dt = self.sun_events.get(key)
                return None if dt is None else dt.hour + dt.minute/60.0 + dt.second/3600.0

            t_aa=_h('dawn_astro'); t_an=_h('dawn_naut'); t_ac=_h('dawn_civ'); t_lv=_h('rise')
            t_co=_h('set');        t_cc=_h('dusk_civ'); t_cn=_h('dusk_naut'); t_ca=_h('dusk_astro')

            _N="#08081A"; _A="#140F28"; _B="#0E1E38"; _C="#2A1C10"; _D="#1E1A0A"

            def _vs(x0, x1, col):
                if x0 is not None and x1 is not None and x0 < x1:
                    self.ax1.axvspan(x0, x1, color=col, alpha=1.0, zorder=0)

            _vs(0,t_aa,_N); _vs(t_aa,t_an,_A); _vs(t_an,t_ac,_B); _vs(t_ac,t_lv,_C)
            _vs(t_lv,t_co,_D); _vs(t_co,t_cc,_C); _vs(t_cc,t_cn,_B); _vs(t_cn,t_ca,_A)
            _vs(t_ca,24,_N)

            self.ax1.plot(self.hours, self.sun_altitudes,
                          color=Config.FG_SUN, linewidth=2, label="Sun")
            self.ax1.plot(self.hours, self.moon_altitudes,
                          color=Config.FG_MOON, linewidth=2, label="Moon")
            self.ax1.axhline(0,   color=Config.FG_RED,    linestyle="--", linewidth=1, alpha=0.7)
            self.ax1.axhline(-6,  color=Config.FG_SUN,    linestyle=":", linewidth=0.7, alpha=0.4)
            self.ax1.axhline(-12, color=Config.BTN_COLOR, linestyle=":", linewidth=0.7, alpha=0.4)
            self.ax1.axhline(-18, color=Config.FG_PURPLE, linestyle=":", linewidth=0.7, alpha=0.4)
            self.ax1.set_xlim(0,24); self.ax1.set_ylim(-90,90)
            self.ax1.set_xticks(range(0,25,2))
            self.ax1.set_xlabel("UT Hour", color=Config.FG_LABEL, fontsize=9)
            self.ax1.set_ylabel("Altitude (°)", color=Config.FG_LABEL, fontsize=9)
            self.ax1.tick_params(colors=Config.FG_LABEL)
            self.ax1.grid(color=Config.GRID_COLOR, linestyle=":")
            self.ax1.legend(loc="upper right", facecolor=Config.BG_PANEL,
                            edgecolor=Config.GRID_COLOR, labelcolor=Config.FG_WHITE)
            self.canvas1.draw_idle()

        # ── Polar sky map ─────────────────────────────────────────────
        self.ax2.clear()
        self.ax2.set_title(
            f"Sky Map  —  {dte_ref.strftime('%H:%M:%S')} UT",
            color=Config.FG_WHITE, pad=12, fontsize=11)
        self.ax2.spines["polar"].set_color(Config.GRID_COLOR)
        self.ax2.set_theta_zero_location("N")
        self.ax2.set_theta_direction(-1)
        self.ax2.set_xticks([math.radians(x) for x in range(0,360,45)])
        self.ax2.set_xticklabels(["N","NE","E","SE","S","SW","W","NW"])
        self.ax2.set_ylim(0,90)
        self.ax2.set_yticks([0,30,60,90])
        self.ax2.set_yticklabels(["","60°","30°","Horizon"],
                                  color=Config.FG_LABEL, fontsize=9)
        self.ax2.tick_params(colors=Config.FG_WHITE)
        self.ax2.grid(color=Config.GRID_COLOR, linestyle="-")

        # Stars
        jd = MeeusEngine.julian_day(dte_ref)
        self.visible_stars = []
        for name, (ra_h, dec_d, mag) in _STARS.items():
            e_alt, e_az = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, ra_h, dec_d)
            if e_alt > 0:
                az_rad = math.radians(e_az); r = 90 - e_alt
                size   = max(2, 10 - mag*3.5)
                self.ax2.plot(az_rad, r, "o", color="#D8E8FF",
                              markersize=size, alpha=0.85, zorder=2)
                if mag < 1.5:
                    self.ax2.annotate(name, xy=(az_rad,r), xytext=(4,4),
                        textcoords="offset points", fontsize=7, color="#A0B8D8", zorder=3)
                self.visible_stars.append((name, mag, az_rad, r, e_alt, e_az))

        # Constellation lines
        star_pos = {name:(az_rad,r) for name,_,az_rad,r,_,_ in self.visible_stars}
        for const_name, edges in CONSTELLATIONS.items():
            pts = []
            for ea, eb in edges:
                if ea in star_pos and eb in star_pos:
                    az_a,r_a = star_pos[ea]; az_b,r_b = star_pos[eb]
                    self.ax2.plot([az_a,az_b],[r_a,r_b],
                                 color="#4A5568", linewidth=0.8, alpha=0.45, zorder=1)
                    pts.extend([(az_a,r_a),(az_b,r_b)])
            if len(pts) >= 4:
                xs = [r*math.cos(az) for az,r in pts]
                ys = [r*math.sin(az) for az,r in pts]
                cx,cy = sum(xs)/len(xs),sum(ys)/len(ys)
                self.ax2.annotate(const_name, xy=(math.atan2(cy,cx),math.hypot(cx,cy)),
                                  fontsize=6, color="#6B7280", alpha=0.7,
                                  ha="center", va="center", zorder=1)

        # Sun and Moon
        if s_alt > 0:
            self.ax2.plot(math.radians(s_az), 90-s_alt, "o",
                          color=Config.FG_SUN, markersize=14, label="Sun", zorder=5)
        if m_alt > 0:
            self.ax2.plot(math.radians(m_az), 90-m_alt, "o",
                          color=Config.FG_MOON, markersize=12, label="Moon", zorder=5)

        # ── Planets on sky map (NEW) ───────────────────────────────────
        self.visible_planets_map = []
        t_ref = MeeusEngine.julian_century_j2000(dte_ref)

        for pname, style in _PLANET_MAP_STYLE.items():
            try:
                p_ra, p_dec, p_dist = MeeusEngine.planet_position(t_ref, pname)
                p_alt, p_az = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, p_ra, p_dec)
                if p_alt > 0:
                    az_rad = math.radians(p_az); r_pol = 90 - p_alt
                    self.ax2.plot(az_rad, r_pol,
                        marker=style["marker"], color=style["color"],
                        markersize=style["size"], zorder=4,
                        markeredgecolor=Config.BG_PANEL, markeredgewidth=0.5)
                    self.ax2.annotate(style["label"], xy=(az_rad,r_pol),
                        xytext=(4,4), textcoords="offset points",
                        fontsize=6.5, color=style["color"], zorder=4)
                    self.visible_planets_map.append({
                        'label': style["label"], 'pname': pname,
                        'az': az_rad, 'r': r_pol,
                        'alt': p_alt, 'az_deg': p_az,
                        'ra': p_ra, 'dec': p_dec, 'dist': p_dist,
                    })
            except Exception:
                pass

        # ── Legend ────────────────────────────────────────────────────
        n      = len(self.visible_stars)
        np_vis = len(self.visible_planets_map)
        handles = [
            plt.Line2D([0],[0], marker="o", color="w",
                markerfacecolor=Config.FG_SUN, markersize=8, label="Sun", linewidth=0),
            plt.Line2D([0],[0], marker="o", color="w",
                markerfacecolor=Config.FG_MOON, markersize=7, label="Moon", linewidth=0),
            plt.Line2D([0],[0], marker="o", color="w",
                markerfacecolor="#D8E8FF", markersize=5, label="Stars", linewidth=0),
        ]
        if np_vis > 0:
            handles.append(
                plt.Line2D([0],[0], marker="D", color="w",
                    markerfacecolor="#C8A870", markersize=5,
                    label=f"Planets ({np_vis})", linewidth=0))

        self.ax2.legend(
            handles=handles, loc="upper right",
            facecolor=Config.BG_PANEL, edgecolor=Config.GRID_COLOR,
            labelcolor=Config.FG_WHITE, fontsize=8,
            title=f"{n} star{'s' if n!=1 else ''} visible",
            title_fontsize=7)

        self.canvas2.draw_idle()
