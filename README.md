# ✨ Céleste — Astronomical Observatory

> Desktop application for calculating and visualising Sun, Moon and planetary positions, based on Jean Meeus's algorithms.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)
![Matplotlib](https://img.shields.io/badge/Charts-Matplotlib-orange)
![Licence](https://img.shields.io/badge/Licence-MIT-green)
![CI](https://github.com/Greg50100/Celeste_App/actions/workflows/ci.yml/badge.svg)

---

## Overview

Céleste calculates in real time — or for any given date — the astronomical positions of the Sun, Moon and four planets (Venus, Mars, Jupiter, Saturn), daily events (rise/set, twilights), lunar phases, eclipse predictions, conjunctions and oppositions. Results are displayed in a modern dark-theme interface with interactive charts and a sky map.

**Core features:**

- **Instant positions** — Right Ascension, Declination, Altitude, Azimuth
- **Daily events** — rise, set, culmination; civil (−6°), nautical (−12°) and astronomical (−18°) twilights
- **Lunar phase** — illumination %, phase name and emoji
- **Real-time mode** — automatic update every 2 s (configurable via settings)
- **Auto-geolocation** — position detection via ip-api.com
- **24 h trajectory chart** — altitude curves with interactive tooltip
- **Polar sky map** — azimuthal projection with N/S/E/W orientation, 32+ named stars, constellation lines, planet markers
- **Solar System tab** — positions of Venus, Mars, Jupiter and Saturn
- **Eclipse predictions** — total / annular / hybrid type, diameter ratio, magnitude, central phase duration
- **Conjunctions & oppositions** — upcoming planetary events
- **Equation of time** — difference between apparent and mean solar time
- **Favourites** — save/load named locations (37 cities pre-loaded)
- **Timezone conversion** — UT → local time via UTC±N selector
- **PDF export** — daily ephemeris export
- **Multilingual UI** — English, French, Spanish, German (switchable via `--lang` or settings)
- **Persistent settings** — theme, language, default place, units, live interval saved to `settings.json`

---

## Installation

### Requirements

- Python 3.10 or higher
- pip

### Clone the repository

```bash
git clone https://github.com/Greg50100/Celeste_App.git
cd Celeste_App
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python main.py
```

### Language options

```bash
python main.py --lang en   # English (default)
python main.py --lang fr   # French
python main.py --lang es   # Spanish
python main.py --lang de   # German
```

---

## Usage

| Field | Description |
|-------|-------------|
| **Date & Time** | Format `DD/MM/YYYY HH:MM:SS` in Universal Time (UT) |
| **Latitude** | Decimal degrees, positive = North (e.g. `48.85` for Paris) |
| **Longitude** | Decimal degrees, positive = East (e.g. `2.35` for Paris) |

**Buttons:**

- `GEOLOC` — Auto-fills latitude and longitude from your IP address
- `⏱ LIVE` — Activates real-time mode (interval configurable in settings)
- `CALCULATE` — Runs calculations for the entered date and coordinates
- `🖨 EXPORT PDF` — Exports today's ephemeris to PDF

**Charts:**

- Hover over the 24 h curve to display the exact altitude at any hour
- The polar chart places Zenith at centre and horizon at edge
- Click a planet marker on the sky map for a detail popup

---

## Architecture

The project follows the **MVC (Model-View-Controller)** pattern:

```
Celeste_App/
├── main.py              # Entry point — i18n init, CTk window
├── engine.py            # Model — pure astronomical calculations (MeeusEngine)
├── gui.py               # View + Controller — interface and application logic
├── utils.py             # Utilities — HMS/DMS formatting, lunar phase labels
├── config.py            # Configuration — colour palette (Catppuccin Mocha theme)
├── i18n.py              # Internationalisation — key-based translation with fallback
├── settings.py          # Persistent user preferences (settings.json)
├── constellations.py    # Star catalog extensions and constellation lines
├── export_pdf.py        # PDF ephemeris export
├── favorites.json       # Pre-loaded locations (37 cities)
├── settings.json        # User preferences (auto-generated)
├── locales/             # Translation files
│   ├── fr.json          # French (reference locale / fallback)
│   ├── en.json          # English
│   ├── es.json          # Spanish
│   └── de.json          # German
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Development dependencies (pytest)
└── tests/
    ├── test_engine.py   # MeeusEngine base algorithms
    ├── test_engine_hp.py# VSOP87, ELP2000, eclipses, conjunctions
    ├── test_i18n.py     # i18n module
    └── test_utils.py    # Formatters (hms, dms, lunar_phase)
```

### Model: `MeeusEngine`

Fully decoupled calculation engine. All methods are class methods or static methods — no internal state is preserved.

| Method | Role |
|--------|------|
| `julian_day(dte)` | Julian Day (JD) |
| `julian_century_j2000(dte)` | T in Julian centuries since J2000.0 |
| `sun_position(t)` | Sun ecliptic longitude + distance — short series (~0.01°) |
| `sun_position_hp(t)` | Sun position — VSOP87 truncated (~1″ arc) |
| `moon_position(t)` | Moon longitude, latitude, parallax — Meeus ch.47 base series |
| `moon_position_elp2000(t)` | Moon position — ELP2000-82B extended series (~10″ arc) |
| `ecliptic_to_equatorial(l, b, t)` | Ecliptic → equatorial (RA, Dec) |
| `equatorial_to_horizontal(jd, lat, lon, ra, dec)` | Equatorial → horizontal (Alt, Az) |
| `elevation_correction(h, p)` | Atmospheric refraction + parallax |
| `find_events(dte, lat, lon, body)` | Rise / set / culmination / twilights |
| `planet_position(name, t)` | Heliocentric → geocentric position (Venus, Mars, Jupiter, Saturn) |
| `equation_of_time(t)` | Equation of time in minutes |
| `angular_separation(ra1, dec1, ra2, dec2)` | Angular separation between two bodies |
| `find_conjunctions(year, body1, body2)` | Upcoming conjunctions / oppositions |
| `find_eclipses(year)` | Solar eclipse predictions with type and magnitude |

### Cache optimisation

The daily event calculation (1440 iterations × 2 bodies) is expensive. A cache keyed on `YYYY-MM-DD_lat_lon` avoids recalculation as long as date and coordinates do not change — particularly useful in real-time mode.

---

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

| File | Scope |
|------|-------|
| `test_engine.py` | Julian Day, Sun/Moon positions, coordinate transforms, event detection, planet positions |
| `test_engine_hp.py` | VSOP87 Sun, ELP2000 Moon, equation of time, angular separation, conjunctions, eclipses |
| `test_i18n.py` | Translation loading, fallback, language switching |
| `test_utils.py` | HMS/DMS formatting (carry propagation), lunar phase labels and normalisation |

---

## Scientific references

- **Jean Meeus**, *Astronomical Algorithms*, 2nd edition, Willmann-Bell, 1998.
  - Chapter 7 — Julian Day
  - Chapter 13 — Coordinate transforms
  - Chapter 16 — Atmospheric refraction (Bennett's formula)
  - Chapter 25 — Sun position (short series, ±0.01°)
  - Chapter 28 — Equation of time
  - Chapter 32 — Sun position VSOP87 (~1″)
  - Chapter 47 — Moon position (base series ±0.01° + ELP2000-82B ±10″)
  - Chapter 54 — Solar eclipse prediction

---

## Dependencies

| Package | Min. version | Role |
|---------|-------------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.2 | Modern dark-mode GUI |
| [matplotlib](https://matplotlib.org/) | 3.10.8 | Interactive astronomical charts |

`tkinter`, `urllib` and `json` are part of the Python standard library.

---

## Road map

### Data & Calculations

- [x] Nautical (−12°) and astronomical (−18°) twilights
- [x] **Solar System** — Venus, Mars, Jupiter, Saturn positions
- [x] **Solar eclipses** — type, magnitude, central phase duration
- [x] **Conjunctions & oppositions** — upcoming planetary events
- [x] **Moon precision** — ELP2000-82B extended series (~10″ arc)
- [x] **Equation of time**
- [ ] **Orrery 2D** — animated planetary orbit visualisation
- [ ] **Lunar eclipses** — extend eclipse detection to the Moon

### Interface & Visualisation

- [x] Main stars on sky map (32+, size proportional to magnitude)
- [x] Constellation lines on polar chart
- [x] Planet markers on sky map (tooltip + click popup)
- [ ] **Twilight colours** — trajectory chart background coloured by phase of day
- [ ] **Interactive sky map** — click a star to display its full data sheet
- [ ] **Light theme** — toggle between Catppuccin Mocha (dark) and Latte (light)

### User Experience

- [x] Favourites — save/load named locations (`favorites.json`)
- [x] Timezone conversion (UT → local time via UTC±N selector)
- [x] **Data export** — daily ephemeris as PDF
- [x] **Multilingual UI** — FR / EN / ES / DE switchable
- [x] **Persistent settings** — language, theme, place, live interval (`settings.json`)
- [ ] **Calculation history** — list of recent calculations, reloadable in one click
- [ ] **Place search** — geocoding by city name
- [ ] **Monthly lunar calendar** — month view with daily phase

### Technical & Quality

- [x] **Unit tests** — pytest on `engine.py`, `utils.py` and `i18n.py` (4 files, ~90 cases)
- [ ] **Executable packaging** — PyInstaller `.exe` (Windows) / `.app` (macOS)

---

## Licence

This project is distributed under the MIT licence. See the `LICENSE` file for details.
