"""
gui.py — Interface graphique Céleste (PyQt6 + Material Design)
===============================================================
v3.2-dev — Refonte complète PyQt6 :
  ★ QMainWindow + QTabWidget (6 onglets)
  ★ Sidebar QWidget avec layout vertical
  ★ Thème Material Design via qt-material
  ★ Format 12h/24h immédiat
  ★ Magnitude limite étoiles
  ★ Onglet ⚙️ Paramètres complet

Architecture :
  - Sidebar gauche  : date, lieu, timezone, favoris, boutons
  - Zone principale : QTabWidget (Éphémérides / Trajectoires /
                      Carte / Planètes / Événements / Paramètres)
  - Barre de statut : coordonnées, étoiles visibles, heure UT
"""

import os
import sys
import json
import math
import urllib.request
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTabWidget,
    QFrame, QScrollArea, QSlider, QCheckBox, QMessageBox,
    QInputDialog, QFileDialog, QSizePolicy, QStatusBar,
    QSplitter, QGroupBox, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from config import Config
from utils import Formatters
from engine import MeeusEngine
from constellations import STARS_EXTRA, CONSTELLATIONS, STAR_CONSTELLATION
import settings as prefs

# ── Constantes ────────────────────────────────────────────────────────────────

_FAVORITES_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "favorites.json")

_UTC_OFFSETS = [f"UTC{'+' if i >= 0 else ''}{i}" for i in range(-12, 15)]

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

_PLANET_MAP_STYLE = {
    "Venus":   {"color": "#D4C060", "marker": "D", "size": 7,  "label": "Venus"},
    "Mars":    {"color": "#E07050", "marker": "D", "size": 7,  "label": "Mars"},
    "Jupiter": {"color": "#C8A870", "marker": "D", "size": 9,  "label": "Jupiter"},
    "Saturn":  {"color": "#C0C060", "marker": "D", "size": 8,  "label": "Saturn"},
}


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _label(text, bold=False, color=None, size=None):
    """Crée un QLabel stylé."""
    lbl = QLabel(text)
    font = lbl.font()
    if bold:
        font.setBold(True)
    if size:
        font.setPointSize(size)
    lbl.setFont(font)
    if color:
        lbl.setStyleSheet(f"color: {color};")
    return lbl


def _btn(text, color=None, flat=False):
    """Crée un QPushButton stylé."""
    b = QPushButton(text)
    if color:
        b.setStyleSheet(
            f"QPushButton {{ background-color: {color}; border-radius: 4px;"
            f" padding: 4px 10px; }}"
            f"QPushButton:hover {{ background-color: {color}cc; }}")
    if flat:
        b.setFlat(True)
    return b


def _sep_h():
    """Séparateur horizontal."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


def _scroll_widget():
    """Retourne (QScrollArea, inner_widget, inner_layout)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)
    scroll.setWidget(inner)
    return scroll, inner, layout


# ── Classe principale ─────────────────────────────────────────────────────────

class AstroApp(QMainWindow):
    """Fenêtre principale de Céleste."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Céleste \u2014 Observatoire Astronomique")
        self.resize(1350, 820)
        self.setMinimumSize(1100, 700)

        # État
        self.live_mode           = False
        self._live_timer         = QTimer(self)
        self._live_timer.timeout.connect(self._live_tick)
        self.last_cache_key      = ""
        self.sun_events          = {}
        self.moon_events         = {}
        self.hours               = []
        self.sun_altitudes       = []
        self.moon_altitudes      = []
        self.utc_offset          = 0
        self.favorites           = self._load_favorites()
        self.visible_stars       = []
        self.visible_planets_map = []
        self._sun_data           = {}
        self._moon_data          = {}
        self.planet_labels       = {}
        self._annot              = None
        self._annot2             = None

        self._build_ui()
        self.calculate()

    # ──────────────────────────────────────────────────────────────────────────
    # CONSTRUCTION UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = self._build_sidebar()
        sidebar.setFixedWidth(270)
        root_layout.addWidget(sidebar)

        # ── Zone principale ───────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        root_layout.addWidget(self.tabs, stretch=1)

        self._build_ephemeris_tab()
        self._build_trajectories_tab()
        self._build_skymap_tab()
        self._build_planets_tab()
        self._build_events_tab()
        self._build_settings_tab()

        # ── Barre de statut ───────────────────────────────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._lbl_pos    = QLabel("\U0001f4cd \u2014")
        self._lbl_stars  = QLabel("")
        self._lbl_time   = QLabel("UT : \u2014")
        self._lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        for w in (self._lbl_pos, self._lbl_stars):
            sb.addWidget(w)
        sb.addPermanentWidget(self._lbl_time)

    # ──────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 6, 10)
        layout.setSpacing(6)

        # Logo
        logo = _label("\U0001f319  C\u00c9LESTE", bold=True, color=Config.FG_MOON, size=16)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addWidget(_sep_h())

        # ── Paramètres ────────────────────────────────────────────────────────
        grp = QGroupBox("Paramètres")
        grp_l = QGridLayout(grp)
        grp_l.setSpacing(6)

        grp_l.addWidget(_label("Date / Heure UT :"), 0, 0)
        self.entry_date = QLineEdit(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        self.entry_date.returnPressed.connect(self.calculate)
        grp_l.addWidget(self.entry_date, 0, 1, 1, 2)

        grp_l.addWidget(_label("Latitude :"), 1, 0)
        self.entry_lat = QLineEdit(str(prefs.get("default_lat") or "49.6333"))
        self.entry_lat.returnPressed.connect(self.calculate)
        grp_l.addWidget(self.entry_lat, 1, 1, 1, 2)

        grp_l.addWidget(_label("Longitude :"), 2, 0)
        self.entry_lon = QLineEdit(str(prefs.get("default_lon") or "-1.6167"))
        self.entry_lon.returnPressed.connect(self.calculate)
        grp_l.addWidget(self.entry_lon, 2, 1)
        btn_geo = QPushButton("\U0001f4cd")
        btn_geo.setFixedWidth(32)
        btn_geo.setToolTip("Géolocalisation automatique")
        btn_geo.clicked.connect(self.geolocate)
        grp_l.addWidget(btn_geo, 2, 2)

        grp_l.addWidget(_label("Fuseau :"), 3, 0)
        self.offset_menu = QComboBox()
        self.offset_menu.addItems(_UTC_OFFSETS)
        _utc = prefs.get("default_utc") or 0
        _utc_str = f"UTC+{_utc}" if _utc >= 0 else f"UTC{_utc}"
        idx = self.offset_menu.findText(_utc_str)
        self.offset_menu.setCurrentIndex(idx if idx >= 0 else 12)
        self.offset_menu.currentTextChanged.connect(self._on_offset_change)
        grp_l.addWidget(self.offset_menu, 3, 1, 1, 2)

        grp_l.setColumnStretch(1, 1)
        layout.addWidget(grp)

        # Bouton Calculer
        self.btn_calc = QPushButton("\U0001f52d  CALCULER")
        self.btn_calc.setMinimumHeight(36)
        self.btn_calc.clicked.connect(self.calculate)
        layout.addWidget(self.btn_calc)

        # Bouton Live
        self.btn_live = QPushButton("\u23f1  LIVE")
        self.btn_live.setCheckable(True)
        self.btn_live.clicked.connect(self.toggle_live)
        layout.addWidget(self.btn_live)

        # Bouton Export PDF
        btn_pdf = QPushButton("\U0001f4c4  EXPORT PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        layout.addWidget(btn_pdf)

        layout.addWidget(_sep_h())

        # ── Favoris ───────────────────────────────────────────────────────────
        grp_fav = QGroupBox("Lieux favoris")
        fav_l = QGridLayout(grp_fav)
        fav_l.setSpacing(4)

        self.combo_fav = QComboBox()
        self.combo_fav.setEditable(False)
        self._refresh_favorites_combo()
        fav_l.addWidget(self.combo_fav, 0, 0)

        btn_apply = QPushButton("\u2714")
        btn_apply.setFixedWidth(30)
        btn_apply.setToolTip("Appliquer ce lieu")
        btn_apply.clicked.connect(self._apply_favorite)
        fav_l.addWidget(btn_apply, 0, 1)

        btn_save_fav = QPushButton("\U0001f4be")
        btn_save_fav.setFixedWidth(30)
        btn_save_fav.setToolTip("Sauvegarder le lieu actuel")
        btn_save_fav.clicked.connect(self.save_location)
        fav_l.addWidget(btn_save_fav, 0, 2)

        btn_del_fav = QPushButton("\U0001f5d1")
        btn_del_fav.setFixedWidth(30)
        btn_del_fav.setToolTip("Supprimer ce favori")
        btn_del_fav.clicked.connect(self.delete_location)
        fav_l.addWidget(btn_del_fav, 0, 3)

        fav_l.setColumnStretch(0, 1)
        layout.addWidget(grp_fav)

        layout.addStretch()
        return sidebar

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 1 — ÉPHÉMÉRIDES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ephemeris_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Soleil ────────────────────────────────────────────────────────────
        sun_box = QGroupBox("☀️  Soleil")
        sun_l = QVBoxLayout(sun_box)
        self._lbl_sun_vis = _label("", color=Config.FG_GREEN, bold=True)
        self._lbl_sun_vis.setAlignment(Qt.AlignmentFlag.AlignRight)
        sun_l.addWidget(self._lbl_sun_vis)
        scroll, _, inner_l = _scroll_widget()
        sun_fields = [
            ("RA",       "Ascension droite"),
            ("Dec",      "Déclinaison"),
            ("Alt",      "Altitude"),
            ("Az",       "Azimut"),
            ("EoT",      "Équation du temps"),
            ("DawnAstro","Aube astro  ▼18°"),
            ("DawnNaut", "Aube naut.  ▼12°"),
            ("Dawn",     "Aube civile  ▼6°"),
            ("Rise",     "Lever"),
            ("Transit",  "Transit"),
            ("Set",      "Coucher"),
            ("Dusk",     "Crép. civil  ▼6°"),
            ("DuskNaut", "Crép. naut. ▼12°"),
            ("DuskAstro","Crép. astro ▼18°"),
        ]
        self.sun_labels = self._make_data_rows(inner_l, sun_fields, Config.FG_SUN)
        sun_l.addWidget(scroll)
        layout.addWidget(sun_box)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # ── Lune ──────────────────────────────────────────────────────────────
        moon_box = QGroupBox("🌙  Lune")
        moon_l = QVBoxLayout(moon_box)
        self._lbl_moon_vis = _label("", color=Config.FG_GREEN, bold=True)
        self._lbl_moon_vis.setAlignment(Qt.AlignmentFlag.AlignRight)
        moon_l.addWidget(self._lbl_moon_vis)
        scroll2, _, inner_l2 = _scroll_widget()
        moon_fields = [
            ("RA",      "Ascension droite"),
            ("Dec",     "Déclinaison"),
            ("Alt",     "Altitude"),
            ("Az",      "Azimut"),
            ("Illum",   "Phase lunaire"),
            ("Rise",    "Lever"),
            ("Transit", "Transit"),
            ("Set",     "Coucher"),
        ]
        self.moon_labels = self._make_data_rows(inner_l2, moon_fields, Config.FG_MOON)
        moon_l.addWidget(scroll2)
        layout.addWidget(moon_box)

        self.tabs.addTab(tab, "☀️🌙  Éphémérides")

    def _make_data_rows(self, layout, fields, val_color):
        TIME_KEYS = {"Rise", "Transit", "Set", "Dawn", "Dusk", "Illum",
                     "DawnNaut", "DuskNaut", "DawnAstro", "DuskAstro"}
        labels = {}
        for key, text in fields:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(4, 2, 4, 2)
            lbl_key = _label(text)
            lbl_key.setMinimumWidth(170)
            lbl_val = _label("\u2014",
                             color=(Config.FG_WHITE if key in TIME_KEYS else val_color),
                             bold=True)
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_l.addWidget(lbl_key)
            row_l.addWidget(lbl_val)
            layout.addWidget(row_w)
            labels[key] = lbl_val
        layout.addStretch()
        return labels

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 2 — TRAJECTOIRES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_trajectories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        self.fig1 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax1  = self.fig1.add_subplot(111, facecolor=Config.BG_PANEL)
        self.fig1.subplots_adjust(left=0.07, right=0.97, top=0.93, bottom=0.08)
        self.canvas1 = FigureCanvasQTAgg(self.fig1)
        self.canvas1.mpl_connect("motion_notify_event", self._on_hover)
        layout.addWidget(self.canvas1)
        self.tabs.addTab(tab, "📈  Trajectoires")

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 3 — CARTE DU CIEL
    # ──────────────────────────────────────────────────────────────────────────

    def _build_skymap_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        self.fig2 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax2  = self.fig2.add_subplot(111, projection='polar',
                                          facecolor=Config.BG_PANEL)
        self.fig2.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.05)
        self.canvas2 = FigureCanvasQTAgg(self.fig2)
        self.canvas2.mpl_connect("motion_notify_event", self._on_hover)
        self.canvas2.mpl_connect("button_press_event", self._on_click_map)
        layout.addWidget(self.canvas2)
        self.tabs.addTab(tab, "🌌  Carte du ciel")

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 4 — PLANÈTES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_planets_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Cartes planètes (gauche)
        left = QWidget()
        left.setFixedWidth(300)
        left_l = QVBoxLayout(left)
        left_l.setSpacing(6)
        _PLANETS_CFG = [
            ("Venus",   "♀  VÉNUS",   "#D4C060"),
            ("Mars",    "♂  MARS",    "#E07050"),
            ("Jupiter", "♃  JUPITER", "#C8A870"),
            ("Saturn",  "♄  SATURNE", "#C0C060"),
        ]
        self.planet_labels = {}
        pl_fields = [
            ("RA", "Ascension droite"), ("Dec", "Déclinaison"),
            ("Alt", "Altitude"), ("Az", "Azimut"), ("Dist", "Distance (UA)"),
        ]
        for pname, ptitle, pcolor in _PLANETS_CFG:
            box = QGroupBox(ptitle)
            box.setStyleSheet(f"QGroupBox {{ color: {pcolor}; font-weight: bold; }}")
            box_l = QVBoxLayout(box)
            box_l.setSpacing(2)
            vis_lbl = _label("", color=Config.FG_GREEN, bold=True)
            vis_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            box_l.addWidget(vis_lbl)
            lbls = self._make_data_rows(box_l, pl_fields, pcolor)
            lbls["_vis"] = vis_lbl
            self.planet_labels[pname] = lbls
            left_l.addWidget(box)
        left_l.addStretch()

        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setFrameShape(QFrame.Shape.NoFrame)
        scroll_left.setWidget(left)
        layout.addWidget(scroll_left)

        # Orréry (droite)
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        self.fig3 = plt.Figure(facecolor=Config.BG_MAIN)
        self.ax3  = self.fig3.add_subplot(111, aspect='equal',
                                          facecolor=Config.BG_PANEL)
        self.fig3.subplots_adjust(left=0.05, right=0.97, top=0.93, bottom=0.05)
        self.canvas3 = FigureCanvasQTAgg(self.fig3)
        right_l.addWidget(self.canvas3)
        layout.addWidget(right, stretch=1)

        self.tabs.addTab(tab, "🪐  Planètes")

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 5 — ÉVÉNEMENTS
    # ──────────────────────────────────────────────────────────────────────────

    def _build_events_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Boutons de recherche
        btn_row = QWidget()
        btn_row_l = QHBoxLayout(btn_row)
        btn_row_l.setContentsMargins(0, 0, 0, 0)
        btn_eclipses = QPushButton("🔭  Rechercher éclipses (12 mois)")
        btn_eclipses.clicked.connect(self._search_eclipses_gui)
        btn_conjunctions = QPushButton("🪐  Rechercher conjonctions (12 mois)")
        btn_conjunctions.clicked.connect(self._search_conjunctions_gui)
        btn_row_l.addWidget(btn_eclipses)
        btn_row_l.addWidget(btn_conjunctions)
        btn_row_l.addStretch()
        layout.addWidget(btn_row)

        # Zone de résultats
        self._evt_scroll, self._evt_inner, self._evt_layout = _scroll_widget()
        self._evt_layout.addWidget(_label("Cliquez un bouton pour lancer la recherche.",
                                          color=Config.FG_LABEL))
        self._evt_layout.addStretch()
        layout.addWidget(self._evt_scroll)

        self.tabs.addTab(tab, "📅  Événements")

    # ──────────────────────────────────────────────────────────────────────────
    # ONGLET 6 — PARAMÈTRES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_settings_tab(self):
        scroll, inner, layout = _scroll_widget()
        layout.setSpacing(10)

        def _section(title):
            lbl = _label(title, bold=True, color=Config.FG_MOON, size=11)
            layout.addWidget(lbl)
            layout.addWidget(_sep_h())

        def _row(label_text, widget):
            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(4, 0, 4, 0)
            lbl = _label(label_text)
            lbl.setFixedWidth(230)
            row_l.addWidget(lbl)
            row_l.addWidget(widget, stretch=1)
            layout.addWidget(row)
            return row

        # ── Apparence ─────────────────────────────────────────────────────────
        _section("🎨  Apparence")

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["mocha", "frapé", "latte"])
        _t = prefs.get("theme") or "mocha"
        _t_disp = {"frape": "frapé"}.get(_t, _t)
        self._theme_combo.setCurrentText(_t_disp)
        self._theme_combo.currentTextChanged.connect(self._on_theme_change)
        _row("Thème (Catppuccin)", self._theme_combo)

        # ── Langue & Format ────────────────────────────────────────────────────
        _section("🌐  Langue & Format")

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["en", "fr", "de", "es"])
        self._lang_combo.setCurrentText(prefs.get("lang") or "en")
        self._lang_combo.currentTextChanged.connect(self._on_lang_change)
        _row("Langue de l'interface", self._lang_combo)

        self._timefmt_combo = QComboBox()
        self._timefmt_combo.addItems(["24h", "12h"])
        self._timefmt_combo.setCurrentText(prefs.get("time_format") or "24h")
        self._timefmt_combo.currentTextChanged.connect(self._on_timefmt_change)
        _row("Format de l'heure", self._timefmt_combo)

        # ── Lieu & Affichage ────────────────────────────────────────────────────
        _section("📍  Lieu & Affichage")

        self._place_entry = QLineEdit(
            prefs.get("default_place") or "\U0001f4cd Cherbourg-en-Cotentin")
        btn_save_place = QPushButton("Sauvegarder")
        btn_save_place.clicked.connect(self._save_default_place)
        place_w = QWidget()
        place_l = QHBoxLayout(place_w)
        place_l.setContentsMargins(0, 0, 0, 0)
        place_l.addWidget(self._place_entry)
        place_l.addWidget(btn_save_place)
        _row("Nom du lieu par défaut", place_w)

        self._autogeo_cb = QCheckBox("Géolocalisation automatique au démarrage")
        self._autogeo_cb.setChecked(bool(prefs.get("auto_geoloc")))
        self._autogeo_cb.toggled.connect(lambda v: prefs.set("auto_geoloc", v))
        layout.addWidget(self._autogeo_cb)

        # Magnitude limite
        mag_w = QWidget()
        mag_l = QHBoxLayout(mag_w)
        mag_l.setContentsMargins(0, 0, 0, 0)
        self._mag_slider = QSlider(Qt.Orientation.Horizontal)
        self._mag_slider.setRange(20, 80)  # x10
        self._mag_slider.setValue(int((prefs.get("mag_limit") or 6.0) * 10))
        self._mag_lbl = _label(f"{(prefs.get('mag_limit') or 6.0):.1f}", bold=True)
        self._mag_lbl.setFixedWidth(36)
        self._mag_slider.valueChanged.connect(self._on_mag_changed)
        mag_l.addWidget(self._mag_slider)
        mag_l.addWidget(self._mag_lbl)
        _row("Magnitude limite (étoiles)", mag_w)

        # Intervalle Live
        iv_w = QWidget()
        iv_l = QHBoxLayout(iv_w)
        iv_l.setContentsMargins(0, 0, 0, 0)
        self._iv_slider = QSlider(Qt.Orientation.Horizontal)
        self._iv_slider.setRange(1, 20)   # x500ms
        self._iv_slider.setValue(int((prefs.get("live_interval") or 2000) / 500))
        self._iv_lbl = _label(f"{prefs.get('live_interval') or 2000} ms", bold=True)
        self._iv_lbl.setFixedWidth(60)
        self._iv_slider.valueChanged.connect(self._on_interval_changed)
        iv_l.addWidget(self._iv_slider)
        iv_l.addWidget(self._iv_lbl)
        _row("Intervalle Live", iv_w)

        # ── Reset ──────────────────────────────────────────────────────────────
        _section("🔄  Réinitialisation")
        btn_reset = QPushButton("🔄  Restaurer les paramètres par défaut")
        btn_reset.clicked.connect(self._reset_settings)
        layout.addWidget(btn_reset)

        info = _label(
            "ℹ️  Le thème et la langue nécessitent un redémarrage pour s'appliquer.",
            color=Config.GRID_COLOR)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        self.tabs.addTab(scroll, "⚙️  Paramètres")

    # ──────────────────────────────────────────────────────────────────────────
    # HANDLERS PARAMÈTRES
    # ──────────────────────────────────────────────────────────────────────────

    def _on_theme_change(self, value):
        prefs.set("theme", value.replace("\u00e9", "e"))
        QMessageBox.information(self, "Thème",
            f"Thème «{value}» sauvegardé.\nRedémarrez l'application pour l'appliquer.")

    def _on_lang_change(self, value):
        prefs.set("lang", value)
        QMessageBox.information(self, "Langue",
            f"Langue «{value}» sauvegardée.\nRedémarrez l'application pour l'appliquer.")

    def _on_timefmt_change(self, value):
        prefs.set("time_format", value)
        self.calculate()

    def _on_mag_changed(self, value):
        mag = value / 10.0
        prefs.set("mag_limit", mag)
        self._mag_lbl.setText(f"{mag:.1f}")
        if self.tabs.currentIndex() == 2:
            self.calculate()

    def _on_interval_changed(self, value):
        iv = value * 500
        prefs.set("live_interval", iv)
        self._iv_lbl.setText(f"{iv} ms")
        if self.live_mode:
            self._live_timer.setInterval(iv)

    def _save_default_place(self):
        name = self._place_entry.text().strip()
        if name:
            prefs.set("default_place", name)
            QMessageBox.information(self, "Paramètres",
                                    f"Lieu par défaut sauvegardé :\n{name}")

    def _reset_settings(self):
        reply = QMessageBox.question(self, "Réinitialiser",
            "Restaurer tous les paramètres par défaut ?\nL'application va redémarrer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            prefs.reset()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    # ──────────────────────────────────────────────────────────────────────────
    # FAVORIS
    # ──────────────────────────────────────────────────────────────────────────

    def _load_favorites(self):
        if os.path.exists(_FAVORITES_FILE):
            try:
                with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_favorites(self):
        with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def _refresh_favorites_combo(self):
        self.combo_fav.clear()
        for name in self.favorites:
            self.combo_fav.addItem(name)

    def _apply_favorite(self):
        name = self.combo_fav.currentText()
        if name in self.favorites:
            loc = self.favorites[name]
            self.entry_lat.setText(str(loc["lat"]))
            self.entry_lon.setText(str(loc["lon"]))
            self.calculate()

    def save_location(self):
        try:
            lat = float(self.entry_lat.text().replace(",", "."))
            lon = float(self.entry_lon.text().replace(",", "."))
        except ValueError:
            QMessageBox.critical(self, "Erreur", "Coordonnées invalides.")
            return
        name, ok = QInputDialog.getText(self, "Sauvegarder", "Nom du lieu :")
        if ok and name.strip():
            name = name.strip()
            self.favorites[name] = {"lat": lat, "lon": lon}
            self._save_favorites()
            self._refresh_favorites_combo()

    def delete_location(self):
        name = self.combo_fav.currentText()
        if name in self.favorites:
            del self.favorites[name]
            self._save_favorites()
            self._refresh_favorites_combo()

    # ──────────────────────────────────────────────────────────────────────────
    # FUSEAU / FORMAT HEURE
    # ──────────────────────────────────────────────────────────────────────────

    def _on_offset_change(self, text):
        val = text.replace("UTC", "").replace("+", "")
        try:
            self.utc_offset = int(val)
        except ValueError:
            self.utc_offset = 0
        self.calculate()

    def _format_event(self, dt):
        if dt is None:
            return "--:--"
        local = dt + timedelta(hours=self.utc_offset)
        if prefs.get("time_format") == "12h":
            return local.strftime("%I:%M %p")
        return local.strftime("%H:%M")

    # ──────────────────────────────────────────────────────────────────────────
    # GÉOLOCALISATION / LIVE
    # ──────────────────────────────────────────────────────────────────────────

    def geolocate(self):
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/",
                headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            if data["status"] == "success":
                self.entry_lat.setText(str(data["lat"]))
                self.entry_lon.setText(str(data["lon"]))
                QMessageBox.information(self, "Géolocalisation",
                    f"Lieu : {data['city']}, {data['country']}")
                self.calculate()
            else:
                QMessageBox.warning(self, "Erreur", "Position indéterminée.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur réseau",
                f"Vérifiez votre connexion.\n{e}")

    def toggle_live(self, checked):
        self.live_mode = checked
        if checked:
            self.btn_live.setText("\u23f8  PAUSE")
            self.entry_date.setReadOnly(True)
            iv = prefs.get("live_interval") or 2000
            self._live_timer.start(iv)
            self._live_tick()
        else:
            self.btn_live.setText("\u23f1  LIVE")
            self.entry_date.setReadOnly(False)
            self._live_timer.stop()

    def _live_tick(self):
        now = datetime.utcnow()
        self.entry_date.setText(now.strftime("%d/%m/%Y %H:%M:%S"))
        self.calculate()

    # ──────────────────────────────────────────────────────────────────────────
    # EXPORT PDF
    # ──────────────────────────────────────────────────────────────────────────

    def export_pdf(self):
        try:
            from export_pdf import generate_report_pdf, build_data_from_app
        except ImportError:
            QMessageBox.critical(self, "Export PDF",
                "Module export_pdf.py introuvable.")
            return
        ts   = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        path, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder le rapport PDF", f"celeste_{ts}.pdf",
            "Fichier PDF (*.pdf)")
        if not path:
            return
        try:
            data = build_data_from_app(self)
            generate_report_pdf(data, path)
            QMessageBox.information(self, "Export PDF",
                f"Rapport sauvegardé :\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", str(e))

    # ──────────────────────────────────────────────────────────────────────────
    # CALCUL PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────

    def calculate(self):
        try:
            s   = self.entry_date.text()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
            lat = float(self.entry_lat.text().replace(",", "."))
            lon = float(self.entry_lon.text().replace(",", "."))
        except ValueError:
            QMessageBox.critical(self, "Erreur",
                "Format de date ou coordonnées invalides.")
            return

        jd = MeeusEngine.julian_day(dte)
        t  = MeeusEngine.julian_century_j2000(dte)

        s_l, _      = MeeusEngine.sun_position(t)
        s_ra, s_dec = MeeusEngine.ecliptic_to_equatorial(s_l, 0, t)
        s_alt, s_az = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, s_ra, s_dec)

        m_l, m_b, m_p = MeeusEngine.moon_position(t)
        m_ra, m_dec   = MeeusEngine.ecliptic_to_equatorial(m_l, m_b, t)
        m_alt, m_az   = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, m_ra, m_dec)
        m_alt_c       = MeeusEngine.elevation_correction(m_alt, m_p)

        phase = MeeusEngine.mod360(m_l - s_l)
        illum = (1 - math.cos(math.radians(phase))) / 2.0 * 100.0

        self._sun_data  = {'name': 'Sun',  'ra': s_ra, 'dec': s_dec,
                           'alt': s_alt, 'az': s_az}
        self._moon_data = {'name': 'Moon', 'ra': m_ra, 'dec': m_dec,
                           'alt': m_alt_c, 'az': m_az,
                           'illum': illum, 'phase': phase}

        key    = f"{dte.strftime('%Y-%m-%d')}_{lat:.2f}_{lon:.2f}"
        redraw = key != self.last_cache_key
        if redraw:
            self.sun_events     = MeeusEngine.find_events(dte, lat, lon, "sun")
            self.moon_events    = MeeusEngine.find_events(dte, lat, lon, "moon")
            self.last_cache_key = key

        eot = MeeusEngine.equation_of_time(t)
        self._update_sun_card(s_ra, s_dec, s_alt, s_az, self.sun_events, eot)
        self._update_moon_card(m_ra, m_dec, m_alt_c, m_az, illum, phase, self.moon_events)
        self._plot_graphs(dte, lat, lon, s_alt, s_az, m_alt_c, m_az, redraw)
        self._calculate_planets(dte, jd, t, lat, lon)
        self._update_status(lat, lon, dte)

    # ──────────────────────────────────────────────────────────────────────────
    # MISE À JOUR DES CARTES
    # ──────────────────────────────────────────────────────────────────────────

    def _update_sun_card(self, ra, dec, alt, az, ev, eot=0.0):
        lb = self.sun_labels
        lb["RA"].setText(f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].setText(f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].setText(f"{alt:.2f}°")
        lb["Az"].setText(f"{az:.2f}°")
        lb["EoT"].setText(f"{eot:+.1f} min")
        lb["DawnAstro"].setText(self._format_event(ev.get("dawn_astro")))
        lb["DawnNaut"].setText(self._format_event(ev.get("dawn_naut")))
        lb["Dawn"].setText(self._format_event(ev.get("dawn_civ")))
        lb["Rise"].setText(self._format_event(ev.get("rise")))
        lb["Transit"].setText(self._format_event(ev.get("transit")))
        lb["Set"].setText(self._format_event(ev.get("set")))
        lb["Dusk"].setText(self._format_event(ev.get("dusk_civ")))
        lb["DuskNaut"].setText(self._format_event(ev.get("dusk_naut")))
        lb["DuskAstro"].setText(self._format_event(ev.get("dusk_astro")))

        if alt > 0:
            self._lbl_sun_vis.setText("✅ VISIBLE")
            self._lbl_sun_vis.setStyleSheet(f"color: {Config.FG_GREEN};")
        elif alt > -6:
            self._lbl_sun_vis.setText("🌄 Crépuscule civil")
            self._lbl_sun_vis.setStyleSheet(f"color: {Config.FG_SUN};")
        elif alt > -12:
            self._lbl_sun_vis.setText("🌅 Crépuscule naut.")
            self._lbl_sun_vis.setStyleSheet(f"color: {Config.BTN_COLOR};")
        elif alt > -18:
            self._lbl_sun_vis.setText("🌃 Crépuscule astro.")
            self._lbl_sun_vis.setStyleSheet(f"color: {Config.FG_PURPLE};")
        else:
            self._lbl_sun_vis.setText("🌑 Nuit noire")
            self._lbl_sun_vis.setStyleSheet(f"color: {Config.FG_RED};")

    def _update_moon_card(self, ra, dec, alt, az, illum, phase, ev):
        lb = self.moon_labels
        lb["RA"].setText(f"{Formatters.hms(ra)}  ({ra:.2f}h)")
        lb["Dec"].setText(f"{Formatters.dms(dec)}  ({dec:.2f}°)")
        lb["Alt"].setText(f"{alt:.2f}°")
        lb["Az"].setText(f"{az:.2f}°")
        lb["Illum"].setText(Formatters.lunar_phase(illum, phase))
        lb["Rise"].setText(self._format_event(ev.get("rise")))
        lb["Transit"].setText(self._format_event(ev.get("transit")))
        lb["Set"].setText(self._format_event(ev.get("set")))
        if alt > 0:
            self._lbl_moon_vis.setText("✅ VISIBLE")
            self._lbl_moon_vis.setStyleSheet(f"color: {Config.FG_GREEN};")
        else:
            self._lbl_moon_vis.setText("⬇ Sous l'horizon")
            self._lbl_moon_vis.setStyleSheet(f"color: {Config.FG_RED};")

    # ──────────────────────────────────────────────────────────────────────────
    # STATUT
    # ──────────────────────────────────────────────────────────────────────────

    def _update_status(self, lat, lon, dte):
        self._lbl_pos.setText(
            f"📍 Lat: {lat:+.4f}°  Lon: {lon:+.4f}°")
        n      = len(self.visible_stars)
        np_vis = len(self.visible_planets_map)
        extra  = f"  🪐 {np_vis} planète(s)" if np_vis else ""
        self._lbl_stars.setText(f"★ {n} étoile(s) visible(s){extra}")
        self._lbl_time.setText(
            f"UT : {dte.strftime('%d/%m/%Y  %H:%M:%S')}")

    # ──────────────────────────────────────────────────────────────────────────
    # PLANÈTES
    # ──────────────────────────────────────────────────────────────────────────

    def _calculate_planets(self, dte, jd, t, lat, lon):
        if not self.planet_labels:
            return
        try:
            from engine import _ORBITAL_ELEMENTS
        except ImportError:
            return
        helio = {}
        for pname, lb in self.planet_labels.items():
            try:
                ra, dec, dist = MeeusEngine.planet_position(t, pname)
                p_alt, p_az  = MeeusEngine.equatorial_to_horizontal(
                    jd, lat, lon, ra, dec)
                lb["RA"].setText(f"{Formatters.hms(ra)}  ({ra:.2f}h)")
                lb["Dec"].setText(f"{Formatters.dms(dec)}  ({dec:.2f}°)")
                lb["Alt"].setText(f"{p_alt:.2f}°")
                lb["Az"].setText(f"{p_az:.2f}°")
                lb["Dist"].setText(f"{dist:.4f} UA")
                if p_alt > 0:
                    lb["_vis"].setText("✅ VISIBLE")
                    lb["_vis"].setStyleSheet(f"color: {Config.FG_GREEN};")
                else:
                    lb["_vis"].setText("⬇ Sous l'horizon")
                    lb["_vis"].setStyleSheet(f"color: {Config.FG_RED};")
                L0, L1, a, *_ = _ORBITAL_ELEMENTS[pname]
                helio[pname] = (a, math.radians(MeeusEngine.mod360(L0 + L1 * t)))
            except Exception:
                pass
        self._plot_orrery(t, helio)

    def _plot_orrery(self, t, helio):
        ax = self.ax3
        ax.clear()
        ax.set_facecolor(Config.BG_PANEL)
        ax.set_title("Système solaire — Vue de dessus",
                     color=Config.FG_WHITE, fontsize=10, pad=8)
        ax.tick_params(colors=Config.FG_LABEL, labelsize=8)
        for sp in ax.spines.values():
            sp.set_color(Config.GRID_COLOR)
        ax.grid(color=Config.GRID_COLOR, linestyle=":", alpha=0.4)
        ax.plot(0, 0, "o", color=Config.FG_SUN, markersize=14, zorder=5)
        ax.annotate("Soleil", xy=(0, 0), xytext=(0.18, 0.05),
                    color=Config.FG_SUN, fontsize=8)
        s_l, r_e = MeeusEngine.sun_position(t)
        l_e  = math.radians(MeeusEngine.mod360(s_l + 180))
        xe, ye = r_e * math.cos(l_e), r_e * math.sin(l_e)
        theta = [i * math.tau / 360 for i in range(361)]
        ax.plot([r_e * math.cos(a) for a in theta],
                [r_e * math.sin(a) for a in theta],
                color=Config.FG_MOON, linewidth=0.5, alpha=0.3)
        ax.plot(xe, ye, "o", color=Config.FG_MOON, markersize=7, zorder=5)
        ax.annotate("Terre", xy=(xe, ye), xytext=(xe+0.1, ye+0.1),
                    color=Config.FG_MOON, fontsize=8)
        _PC = {"Venus": "#D4C060", "Mars": "#E07050",
               "Jupiter": "#C8A870", "Saturn": "#C0C060"}
        _PS = {"Venus": 6, "Mars": 6, "Jupiter": 9, "Saturn": 8}
        for pname, (a, l_rad) in helio.items():
            xp, yp = a * math.cos(l_rad), a * math.sin(l_rad)
            color  = _PC.get(pname, "#AAAAAA")
            ax.plot([a * math.cos(ang) for ang in theta],
                    [a * math.sin(ang) for ang in theta],
                    color=color, linewidth=0.5, alpha=0.25)
            ax.plot(xp, yp, "o", color=color,
                    markersize=_PS.get(pname, 6), zorder=4)
            ax.annotate(pname, xy=(xp, yp), xytext=(xp+0.1, yp+0.15),
                        color=color, fontsize=8)
        lim = 11.0
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.set_xlabel("UA", color=Config.FG_LABEL, fontsize=8)
        ax.set_ylabel("UA", color=Config.FG_LABEL, fontsize=8)
        self.canvas3.draw_idle()


    # ── Trajectoires + Carte du ciel ─────────────────────────────────────────
    def _plot_graphs(self, dte, lat, lon, s_alt, s_az, m_alt, m_az, redraw):
        """Trace les courbes 24h (ax1) et la carte polaire (ax2)."""
        mag_limit = prefs.get("mag_limit") or 6.0

        # ── Courbes 24h ──────────────────────────────────────────────────────
        if redraw:
            hours, sun_alts, moon_alts = [], [], []
            base = dte.replace(hour=0, minute=0, second=0, microsecond=0)
            for h in range(0, 1441, 15):
                d    = base + timedelta(minutes=h)
                jd_h = MeeusEngine.julian_day(d)
                t_h  = MeeusEngine.julian_century_j2000(d)
                sl, _ = MeeusEngine.sun_position(t_h)
                sr, sd = MeeusEngine.ecliptic_to_equatorial(sl, 0, t_h)
                sa, _  = MeeusEngine.equatorial_to_horizontal(jd_h, lat, lon, sr, sd)
                ml, mb, mp = MeeusEngine.moon_position(t_h)
                mr, md = MeeusEngine.ecliptic_to_equatorial(ml, mb, t_h)
                ma, _  = MeeusEngine.equatorial_to_horizontal(jd_h, lat, lon, mr, md)
                hours.append(h / 60)
                sun_alts.append(sa)
                moon_alts.append(MeeusEngine.elevation_correction(ma, mp))
            self.hours          = hours
            self.sun_altitudes  = sun_alts
            self.moon_altitudes = moon_alts

        ax = self.ax1
        ax.clear()
        ax.set_facecolor(Config.BG_PANEL)
        ax.set_title("Trajectoires 24h \u2014 Soleil & Lune",
                     color=Config.FG_WHITE, fontsize=11, pad=8)
        ax.tick_params(colors=Config.FG_LABEL, labelsize=9)
        for sp in ax.spines.values():
            sp.set_color(Config.GRID_COLOR)
        ax.grid(color=Config.GRID_COLOR, linestyle=":", alpha=0.4)
        ax.axhline(0, color=Config.FG_RED, linewidth=0.8, alpha=0.6)
        ax.plot(self.hours, self.sun_altitudes,
                color=Config.FG_SUN, linewidth=2, label="Soleil")
        ax.plot(self.hours, self.moon_altitudes,
                color=Config.FG_MOON, linewidth=2, label="Lune")
        h_now = dte.hour + dte.minute / 60 + dte.second / 3600
        ax.axvline(h_now, color=Config.FG_WHITE,
                   linewidth=1, alpha=0.5, linestyle="--")
        ax.plot(h_now, s_alt, "o", color=Config.FG_SUN,  markersize=8, zorder=5)
        ax.plot(h_now, m_alt, "o", color=Config.FG_MOON, markersize=8, zorder=5)
        ax.set_xlim(0, 24)
        ax.set_xlabel("Heure UT", color=Config.FG_LABEL, fontsize=9)
        ax.set_ylabel("Altitude (\u00b0)", color=Config.FG_LABEL, fontsize=9)
        ax.legend(facecolor=Config.BG_PANEL, edgecolor=Config.GRID_COLOR,
                  labelcolor=Config.FG_WHITE, fontsize=9)
        self.canvas1.draw_idle()

        # ── Carte polaire du ciel ─────────────────────────────────────────────
        jd  = MeeusEngine.julian_day(dte)
        t   = MeeusEngine.julian_century_j2000(dte)
        ax2 = self.ax2
        ax2.clear()
        ax2.set_facecolor(Config.BG_PANEL)
        ax2.set_title("Carte du ciel", color=Config.FG_WHITE, fontsize=11, pad=12)
        ax2.tick_params(colors=Config.FG_LABEL, labelsize=8)
        ax2.set_theta_zero_location("N")
        ax2.set_theta_direction(-1)
        ax2.set_rlim(0, 1)
        ax2.yaxis.set_visible(False)
        ax2.set_xticks([math.radians(a) for a in range(0, 360, 45)])
        ax2.set_xticklabels(["N", "NE", "E", "SE", "S", "SO", "O", "NO"],
                            color=Config.FG_LABEL)
        self.visible_stars      = []
        self._star_scatter_data = []
        for sname, (ra_h, dec_d, mag) in _STARS.items():
            if mag > mag_limit:
                continue
            alt, az = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, ra_h, dec_d)
            if alt < -2:
                continue
            r, theta = (90 - max(alt, 0)) / 90, math.radians(az)
            size  = max(2, (mag_limit - mag + 1) * 8)
            alpha = min(1.0, max(0.4, 1.0 - mag / 8.0))
            ax2.plot(theta, r, "o", color=Config.FG_WHITE,
                     markersize=size, alpha=alpha, zorder=3)

            if mag < 2.5:
                ax2.annotate(sname, xy=(theta, r),
                             xytext=(theta + 0.03, r + 0.03),
                             color=Config.FG_LABEL, fontsize=7,
                             annotation_clip=False)
            self.visible_stars.append(sname)
            self._star_scatter_data.append((theta, r, sname, mag, alt, az))

        # Lignes de constellations
        for cname, edges in CONSTELLATIONS.items():
            for star_a, star_b in edges:
                if star_a not in _STARS or star_b not in _STARS:
                    continue
                ra1, dec1, _ = _STARS[star_a]
                ra2, dec2, _ = _STARS[star_b]
                alt1, az1 = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, ra1, dec1)
                alt2, az2 = MeeusEngine.equatorial_to_horizontal(jd, lat, lon, ra2, dec2)
                if alt1 < 0 and alt2 < 0:
                    continue
                r1, theta1 = (90 - max(alt1, 0)) / 90, math.radians(az1)
                r2, theta2 = (90 - max(alt2, 0)) / 90, math.radians(az2)
                ax2.plot([theta1, theta2], [r1, r2],
                         color=Config.GRID_COLOR,
                         linewidth=0.7, alpha=0.4, zorder=1)

        # Soleil
        ax2.plot(math.radians(s_az), (90 - max(s_alt, 0)) / 90,
                 "*", color=Config.FG_SUN, markersize=14, zorder=6)
        ax2.annotate("Soleil",
                     xy=(math.radians(s_az), (90 - max(s_alt, 0)) / 90),
                     xytext=(math.radians(s_az) + 0.05, (90 - max(s_alt, 0)) / 90 + 0.05),
                     color=Config.FG_SUN, fontsize=8, annotation_clip=False)
        # Lune
        ax2.plot(math.radians(m_az), (90 - max(m_alt, 0)) / 90,
                 "o", color=Config.FG_MOON, markersize=10, zorder=6)
        ax2.annotate("Lune",
                     xy=(math.radians(m_az), (90 - max(m_alt, 0)) / 90),
                     xytext=(math.radians(m_az) + 0.05, (90 - max(m_alt, 0)) / 90 + 0.05),
                     color=Config.FG_MOON, fontsize=8, annotation_clip=False)
        # Planetes visibles
        self.visible_planets_map = []
        for pname, style in _PLANET_MAP_STYLE.items():
            try:
                p_ra, p_dec, _ = MeeusEngine.planet_position(t, pname)
                p_alt, p_az    = MeeusEngine.equatorial_to_horizontal(
                    jd, lat, lon, p_ra, p_dec)
                if p_alt >= -2:
                    r_p, theta_p = (90 - max(p_alt, 0)) / 90, math.radians(p_az)
                    ax2.plot(theta_p, r_p, marker=style["marker"],
                             color=style["color"], markersize=style["size"], zorder=5)
                    ax2.annotate(style["label"], xy=(theta_p, r_p),
                                 xytext=(theta_p + 0.04, r_p + 0.04),
                                 color=style["color"], fontsize=8,
                                 annotation_clip=False)
                    self.visible_planets_map.append((pname, theta_p, r_p, p_alt, p_az))
            except Exception:
                pass

        self._annot2 = ax2.annotate(
            "", xy=(0, 0), xytext=(0.1, 0.1),
            fontsize=8, color=Config.FG_WHITE,
            bbox=dict(boxstyle="round,pad=0.3", fc=Config.BG_PANEL,
                      ec=Config.GRID_COLOR, alpha=0.9),
            annotation_clip=False)
        self._annot2.set_visible(False)
        self.canvas2.draw_idle()

    # ── Survol ───────────────────────────────────────────────────────────────
    def _on_hover(self, event):
        """Tooltip au survol canvas1 (trajectoires) et canvas2 (carte)."""
        if event.inaxes is None:
            return

        if event.canvas is self.canvas1:
            if not self.hours or event.xdata is None:
                return
            idx = min(range(len(self.hours)),
                      key=lambda i: abs(self.hours[i] - event.xdata))
            sa = self.sun_altitudes[idx]  if idx < len(self.sun_altitudes)  else None
            ma = self.moon_altitudes[idx] if idx < len(self.moon_altitudes) else None
            if sa is None:
                return
            tip = (f"UT {self.hours[idx]:05.2f}h\n"
                   f"\u2600 {sa:+.1f}\u00b0\n"
                   f"\U0001f319 {ma:+.1f}\u00b0")
            if self._annot is None:
                self._annot = self.ax1.annotate(
                    tip, xy=(event.xdata, event.ydata),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=8, color=Config.FG_WHITE,
                    bbox=dict(boxstyle="round,pad=0.3", fc=Config.BG_PANEL,
                              ec=Config.GRID_COLOR, alpha=0.9))
            else:
                self._annot.set_text(tip)
                self._annot.xy = (event.xdata, event.ydata)
                self._annot.set_visible(True)
            self.canvas1.draw_idle()

        elif event.canvas is self.canvas2 and self._annot2 is not None:
            if not hasattr(self, "_star_scatter_data"):
                return
            x, y = event.xdata, event.ydata
            if x is None or y is None:
                return
            best_dist, best_name = 0.1, None
            for (th, r, sname, mag, alt, az) in self._star_scatter_data:
                dist = math.hypot(th - x, r - y)
                if dist < best_dist:
                    best_dist = dist
                    best_name = (f"{sname}\n"
                                 f"Alt {alt:.1f}\u00b0  Az {az:.1f}\u00b0  "
                                 f"Mag {mag:.1f}")
            for (pname, th, r, alt, az) in self.visible_planets_map:
                dist = math.hypot(th - x, r - y)
                if dist < best_dist:
                    best_dist = dist
                    best_name = (f"{pname}\n"
                                 f"Alt {alt:.1f}\u00b0  Az {az:.1f}\u00b0")
            if best_name:
                self._annot2.set_text(best_name)
                self._annot2.xy = (x, y)
                self._annot2.set_visible(True)
            else:
                self._annot2.set_visible(False)
            self.canvas2.draw_idle()

    # ── Clic sur la carte ────────────────────────────────────────────────────
    def _on_click_map(self, event):
        """Clic sur la carte du ciel -> popup de detail."""
        if event.inaxes is None or not hasattr(self, "_star_scatter_data"):
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        best_dist, best_obj = 0.08, None
        for (th, r, sname, mag, alt, az) in self._star_scatter_data:
            dist = math.hypot(th - x, r - y)
            if dist < best_dist:
                best_dist = dist
                best_obj  = {"type": "star", "name": sname,
                             "mag": mag, "alt": alt, "az": az}
        for (pname, th, r, alt, az) in self.visible_planets_map:
            dist = math.hypot(th - x, r - y)
            if dist < best_dist:
                best_dist = dist
                best_obj  = {"type": "planet", "name": pname,
                             "alt": alt, "az": az}
        if best_obj:
            self._show_object_detail(best_obj)

    def _show_object_detail(self, obj):
        """QDialog de detail pour un objet celeste."""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle(f"D\u00e9tail \u2014 {obj['name']}")
        dlg.setMinimumWidth(300)
        vlay = QVBoxLayout(dlg)
        vlay.addWidget(_label(obj["name"], bold=True, size=13,
                              color=Config.FG_MOON))
        vlay.addWidget(_sep_h())

        if obj["type"] == "star":
            rows = [("Type",      "\u00c9toile"),
                    ("Magnitude", f"{obj['mag']:.2f}"),
                    ("Altitude",  f"{obj['alt']:.2f}\u00b0"),
                    ("Azimut",    f"{obj['az']:.2f}\u00b0")]
            if obj["name"] in STAR_CONSTELLATION:
                rows.insert(1, ("Constellation",
                                STAR_CONSTELLATION[obj["name"]]))
        else:
            rows = [("Type",     "Plan\u00e8te"),
                    ("Altitude", f"{obj['alt']:.2f}\u00b0"),
                    ("Azimut",   f"{obj['az']:.2f}\u00b0")]
        for key, val in rows:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(4, 2, 4, 2)
            lbl_k = _label(key)
            lbl_k.setFixedWidth(130)
            lbl_v = _label(val, bold=True, color=Config.FG_WHITE)
            row_l.addWidget(lbl_k)
            row_l.addWidget(lbl_v)
            vlay.addWidget(row_w)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(dlg.accept)
        vlay.addWidget(bb)
        dlg.exec()

    # ── Nettoyage zone evenements ────────────────────────────────────────────
    def _clear_evt_layout(self):
        while self._evt_layout.count():
            item = self._evt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Eclipses ─────────────────────────────────────────────────────────────
    def _search_eclipses_gui(self):
        """Recherche et affiche les eclipses sur 12 mois."""
        try:
            s   = self.entry_date.text()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            QMessageBox.critical(self, "Erreur", "Date invalide.")
            return
        self._clear_evt_layout()
        self._evt_layout.addWidget(
            _label("\U0001f311  \u00c9clipses \u2014 12 prochains mois",
                   bold=True, color=Config.FG_MOON, size=12))
        self._evt_layout.addWidget(_sep_h())
        try:
            eclipses = MeeusEngine.find_eclipses(dte, num_months=12)
        except Exception as e:
            self._evt_layout.addWidget(
                _label(f"Erreur : {e}", color=Config.FG_RED))
            self._evt_layout.addStretch()
            return
        if not eclipses:
            self._evt_layout.addWidget(
                _label("Aucune \u00e9clipse trouv\u00e9e sur cette p\u00e9riode.",
                       color=Config.FG_LABEL))
        else:
            for ec in eclipses:
                row   = QWidget()
                row_l = QHBoxLayout(row)
                row_l.setContentsMargins(8, 4, 8, 4)

                etype = ec.get("type", "?")
                edate = ec.get("date", "")
                emag  = ec.get("magnitude", None)
                esub  = ec.get("sub_type", "")
                if isinstance(edate, datetime):
                    edate = edate.strftime("%d/%m/%Y %H:%M UT")
                is_solar  = (etype == "solar")
                color     = Config.FG_SUN if is_solar else Config.FG_MOON
                icon      = "\u2600" if is_solar else "\U0001f311"
                lbl_txt   = f"{icon}  {etype.capitalize()}"
                if esub:
                    lbl_txt += f" ({esub})"
                lbl_type = _label(lbl_txt, bold=True, color=color)
                lbl_type.setFixedWidth(240)
                lbl_date = _label(str(edate), color=Config.FG_WHITE)
                row_l.addWidget(lbl_type)
                row_l.addWidget(lbl_date)
                if emag is not None:
                    row_l.addWidget(_label(f"Mag {emag:.3f}",
                                           color=Config.FG_LABEL))
                row_l.addStretch()
                row.setStyleSheet(f"background-color: {Config.BG_PANEL};"
                                  " border-radius:4px; margin:2px;")
                self._evt_layout.addWidget(row)
        self._evt_layout.addStretch()

    # ── Conjonctions ─────────────────────────────────────────────────────────
    def _search_conjunctions_gui(self):
        """Recherche et affiche les conjonctions planetaires sur 12 mois."""
        try:
            s   = self.entry_date.text()
            fmt = "%d/%m/%Y %H:%M:%S" if s.count(":") == 2 else "%d/%m/%Y %H:%M"
            dte = datetime.strptime(s, fmt)
        except ValueError:
            QMessageBox.critical(self, "Erreur", "Date invalide.")
            return
        self._clear_evt_layout()
        self._evt_layout.addWidget(
            _label("\U0001f31f  Conjonctions plan\u00e9taires \u2014 12 mois",
                   bold=True, color=Config.FG_MOON, size=12))
        self._evt_layout.addWidget(_sep_h())
        try:
            conjs = MeeusEngine.find_conjunctions(dte, num_days=365)
        except Exception as e:
            self._evt_layout.addWidget(
                _label(f"Erreur : {e}", color=Config.FG_RED))
            self._evt_layout.addStretch()
            return
        if not conjs:
            self._evt_layout.addWidget(
                _label("Aucune conjonction trouv\u00e9e sur cette p\u00e9riode.",
                       color=Config.FG_LABEL))
        else:
            for cj in conjs:
                row   = QWidget()
                row_l = QHBoxLayout(row)
                row_l.setContentsMargins(8, 4, 8, 4)

                ctype  = cj.get("type", "conjunction")
                bodies = cj.get("bodies", ("?", "?"))
                cdate  = cj.get("date", "")
                csep   = cj.get("separation", None)
                if isinstance(cdate, datetime):
                    cdate = cdate.strftime("%d/%m/%Y %H:%M UT")
                if hasattr(bodies, "__iter__") and not isinstance(bodies, str):
                    bodies_str = " \u2014 ".join(bodies)
                else:
                    bodies_str = str(bodies)
                icon  = "\U0001f31f" if ctype == "conjunction" else "\u21c4"
                lbl_b = _label(f"{icon}  {bodies_str}",
                               bold=True, color=Config.FG_MOON)
                lbl_b.setFixedWidth(240)
                lbl_d = _label(str(cdate), color=Config.FG_WHITE)
                row_l.addWidget(lbl_b)
                row_l.addWidget(lbl_d)
                if csep is not None:
                    row_l.addWidget(_label(f"S\u00e9par. {csep:.2f}\u00b0",
                                           color=Config.FG_LABEL))
                row_l.addStretch()
                row.setStyleSheet(f"background-color: {Config.BG_PANEL};"
                                  " border-radius:4px; margin:2px;")
                self._evt_layout.addWidget(row)
        self._evt_layout.addStretch()
