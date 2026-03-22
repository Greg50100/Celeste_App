"""
engine.py — Astronomical Calculation Engine for Céleste
=========================================================
Implements the algorithms of Jean Meeus (Astronomical Algorithms, 2nd ed.)
for calculating Sun, Moon and planetary positions, as well as detecting
daily events (sunrise, sunset, twilights).

This module is completely independent from the graphical interface (MVC model).
"""

import math
from datetime import timedelta

# ==========================================================
# 3. JEAN MEEUS MATHEMATICAL ENGINE (THE MODEL)
# ==========================================================

# Atmospheric refraction correction (Meeus, chap. 16)
# The Sun is considered risen when its center is at -0.833° below the geometric horizon
# (0.5° apparent semi-diameter + 0.333° standard refraction)
_HORIZON_CORRECTION_SUN = 0.833  # degrees

# Refraction coefficients for Bennett's formula (Meeus, chap. 16)
_REFRACTION_A = 10.3   # angular coefficient
_REFRACTION_B = 5.11   # angular offset

# Mean orbital elements at J2000.0 for visible planets.
# Format: [L0 (°), L1 (°/century), a (AU), e0, e1 (/century), i (°), Ω (°), ω̃ (°)]
#   L  = mean longitude      a  = semi-major axis
#   e  = eccentricity        i  = inclination on ecliptic
#   Ω  = longitude of ascending node  ω̃  = longitude of perihelion
# Source: Meeus, Astronomical Algorithms, 2nd ed., Table 31.a / App. II.
_ORBITAL_ELEMENTS = {
    "Venus":   [181.979801,  58517.8156760, 0.72333199,  0.00677323, -0.00004938,  3.39471,  76.68069, 131.53298],
    "Mars":    [355.433275,  19140.2993313, 1.52366231,  0.09341233,  0.00011902,  1.85061,  49.57854, 336.04084],
    "Jupiter": [ 34.351519,   3034.9056606, 5.20336301,  0.04839266, -0.00012880,  1.30530, 100.55615,  14.75385],
    "Saturn":  [ 50.077444,   1222.1137943, 9.53707032,  0.05415060, -0.00036762,  2.48446, 113.71504,  92.43194],
}

# ── Meeus tables, chapter 47 — Periodic terms for the Moon ────────────
# Each term: (coeff_D, coeff_M, coeff_Mp, coeff_F, amplitude)
# Longitude: amplitude in 0.000001° (micro-degrees), to multiply by sin(arg)
# Distance: amplitude in 0.001 km (milli-km), to multiply by cos(arg)
_MOON_LONGITUDE_TERMS = (
    ( 0,  0,  1,  0,  6288774),
    ( 2,  0, -1,  0, -1274027),
    ( 2,  0,  0,  0,   658314),
    ( 0,  0,  2,  0,   213618),
    ( 0,  1,  0,  0,  -185116),
    ( 0,  0,  0,  2,  -114332),
    ( 2,  0, -2,  0,    58793),
    ( 2, -1, -1,  0,    57066),
    ( 2,  0,  1,  0,    53322),
    ( 2, -1,  0,  0,    45758),
    ( 0,  1, -1,  0,   -40923),
    ( 1,  0,  0,  0,   -34720),
    ( 0,  1,  1,  0,   -30383),
    ( 2,  0,  0, -2,    15327),
    ( 0,  0,  1,  2,   -12528),
    ( 0,  0,  1, -2,    10980),
    ( 4,  0, -1,  0,    10675),
    ( 0,  0,  3,  0,    10034),
    ( 4,  0, -2,  0,     8548),
    ( 2,  1, -1,  0,    -7888),
    ( 2,  1,  0,  0,    -6766),
    ( 1,  0, -1,  0,    -5163),
    ( 1,  1,  0,  0,     4987),
    ( 2, -1,  1,  0,     4036),
    ( 2,  0,  2,  0,     3994),
    ( 4,  0,  0,  0,     3861),
    ( 2,  0, -3,  0,     3665),
    ( 0,  1, -2,  0,    -2689),
    ( 2,  0, -1,  2,    -2602),
    ( 2, -1, -2,  0,     2390),
    ( 1,  0,  1,  0,    -2348),
    ( 2, -2,  0,  0,     2236),
    ( 0,  1,  2,  0,    -2120),
    ( 0,  2,  0,  0,    -2069),
    ( 2, -2, -1,  0,     2048),
    ( 2,  0,  1, -2,    -1773),
    ( 2,  0,  0,  2,    -1595),
    ( 4, -1, -1,  0,     1215),
    ( 0,  0,  2,  2,    -1110),
    ( 3,  0, -1,  0,     -892),
    ( 2,  1,  1,  0,     -810),
    ( 4, -1, -2,  0,      759),
    ( 0,  2, -1,  0,     -713),
    ( 2,  2, -1,  0,     -700),
    ( 2,  1, -2,  0,      691),
    ( 2, -1,  0, -2,      596),
    ( 4,  0,  1,  0,      549),
    ( 0,  0,  4,  0,      537),
    ( 4, -1,  0,  0,      520),
    ( 1,  0, -2,  0,     -487),
    ( 2,  1,  0, -2,     -399),
    ( 0,  0,  2, -2,     -381),
    ( 1,  1,  1,  0,      351),
    ( 3,  0, -2,  0,     -340),
    ( 4,  0, -3,  0,      330),
    ( 2, -1,  2,  0,      327),
    ( 0,  2,  1,  0,     -323),
    ( 1,  1, -1,  0,      299),
    ( 2,  0,  3,  0,      294),
    ( 2,  0, -1, -2,        0),
)

_MOON_DISTANCE_TERMS = (
    ( 0,  0,  1,  0, -20905355),
    ( 2,  0, -1,  0,  -3699111),
    ( 2,  0,  0,  0,  -2955968),
    ( 0,  0,  2,  0,   -569925),
    ( 0,  1,  0,  0,     48888),
    ( 0,  0,  0,  2,     -3149),
    ( 2,  0, -2,  0,    246158),
    ( 2, -1, -1,  0,   -152138),
    ( 2,  0,  1,  0,   -170733),
    ( 2, -1,  0,  0,   -204586),
    ( 0,  1, -1,  0,   -129620),
    ( 1,  0,  0,  0,    108743),
    ( 0,  1,  1,  0,    104755),
    ( 2,  0,  0, -2,     10321),
    ( 0,  0,  1,  2,         0),
    ( 0,  0,  1, -2,     79661),
    ( 4,  0, -1,  0,    -34782),
    ( 0,  0,  3,  0,    -23210),
    ( 4,  0, -2,  0,    -21636),
    ( 2,  1, -1,  0,     24208),
    ( 2,  1,  0,  0,     30824),
    ( 1,  0, -1,  0,     -8379),
    ( 1,  1,  0,  0,    -16675),
    ( 2, -1,  1,  0,    -12831),
    ( 2,  0,  2,  0,    -10445),
    ( 4,  0,  0,  0,    -11650),
    ( 2,  0, -3,  0,     14403),
    ( 0,  1, -2,  0,     -7003),
    ( 2,  0, -1,  2,         0),
    ( 2, -1, -2,  0,     10056),
    ( 1,  0,  1,  0,      6322),
    ( 2, -2,  0,  0,     -9884),
    ( 0,  1,  2,  0,      5751),
    ( 0,  2,  0,  0,         0),
    ( 2, -2, -1,  0,     -4950),
    ( 2,  0,  1, -2,         0),
    ( 2,  0,  0,  2,      4130),
    ( 4, -1, -1,  0,         0),
    ( 0,  0,  2,  2,     -3958),
    ( 3,  0, -1,  0,         0),
    ( 2,  1,  1,  0,      3258),
    ( 4, -1, -2,  0,      2616),
    ( 0,  2, -1,  0,     -1897),
    ( 2,  2, -1,  0,     -2117),
    ( 2,  1, -2,  0,      2354),
    ( 2, -1,  0, -2,         0),
    ( 4,  0,  1,  0,         0),
    ( 0,  0,  4,  0,     -1423),
    ( 4, -1,  0,  0,     -1117),
    ( 1,  0, -2,  0,     -1571),
    ( 2,  1,  0, -2,     -1739),
    ( 0,  0,  2, -2,         0),
    ( 1,  1,  1,  0,         0),
    ( 3,  0, -2,  0,     -4421),
    ( 4,  0, -3,  0,         0),
    ( 2, -1,  2,  0,         0),
    ( 0,  2,  1,  0,      1165),
    ( 1,  1, -1,  0,         0),
    ( 2,  0,  3,  0,         0),
    ( 2,  0, -1, -2,      8752),
)

_MOON_LATITUDE_TERMS = (
    ( 0,  0,  0,  1,  5128122),
    ( 0,  0,  1,  1,   280602),
    ( 0,  0,  1, -1,   277693),
    ( 2,  0,  0, -1,   173237),
    ( 2,  0, -1,  1,    55413),
    ( 2,  0, -1, -1,    46271),
    ( 2,  0,  0,  1,    32573),
    ( 0,  0,  2,  1,    17198),
    ( 2,  0,  1, -1,     9266),
    ( 0,  0,  2, -1,     8822),
    ( 2, -1,  0, -1,     8216),
    ( 2,  0, -2, -1,     4324),
    ( 2,  0,  1,  1,     4200),
    ( 2,  1,  0, -1,    -3359),
    ( 2, -1, -1,  1,     2463),
    ( 2, -1,  0,  1,     2211),
    ( 2, -1, -1, -1,     2065),
    ( 0,  1, -1, -1,    -1870),
    ( 4,  0, -1, -1,     1828),
    ( 0,  1,  0,  1,    -1794),
    ( 0,  0,  0,  3,    -1749),
    ( 0,  1, -1,  1,    -1565),
    ( 1,  0,  0,  1,    -1491),
    ( 0,  1,  1,  1,    -1475),
    ( 0,  1,  1, -1,    -1410),
    ( 0,  1,  0, -1,    -1344),
    ( 1,  0,  0, -1,    -1335),
    ( 0,  0,  3,  1,     1107),
    ( 4,  0,  0, -1,     1021),
    ( 4,  0, -1,  1,      833),
    ( 0,  0,  1, -3,      777),
    ( 4,  0, -2,  1,      671),
    ( 2,  0,  0, -3,      607),
    ( 2,  0,  2, -1,      596),
    ( 2, -1,  1, -1,      491),
    ( 2,  0, -2,  1,     -451),
    ( 0,  0,  3, -1,      439),
    ( 2,  0,  2,  1,      422),
    ( 2,  0, -3, -1,      421),
    ( 2,  1, -1,  1,     -366),
    ( 2,  1,  0,  1,     -351),
    ( 4,  0,  0,  1,      331),
    ( 2, -1,  1,  1,      315),
    ( 2, -2,  0, -1,      302),
    ( 0,  0,  1,  3,     -283),
    ( 2,  1,  1, -1,     -229),
    ( 1,  1,  0, -1,      223),
    ( 1,  1,  0,  1,      223),
    ( 0,  1, -2, -1,     -220),
    ( 2,  1, -1, -1,     -220),
    ( 1,  0,  1,  1,     -185),
    ( 2, -1, -2, -1,      181),
    ( 0,  1,  2,  1,     -177),
    ( 4,  0, -2, -1,      176),
    ( 4, -1, -1, -1,      166),
    ( 1,  0,  1, -1,     -164),
    ( 4,  0,  1, -1,      132),
    ( 1,  0, -1, -1,     -119),
    ( 4, -1,  0, -1,      115),
    ( 2, -2,  0,  1,      107),
)


class MeeusEngine:
    """
    Encapsulates all pure astronomical calculations, independent of the interface.

    All methods are class methods or static methods: no internal state is preserved
    between calls. The caller provides temporal and geographic parameters at each invocation.

    Reference: Jean Meeus, *Astronomical Algorithms*, 2nd ed., Willmann-Bell, 1998.
    """

    @staticmethod
    def mod360(a):
        """Returns an angle to the interval [0, 360[."""
        return a % 360

    @classmethod
    def julian_day(cls, dte):
        """
        Calculates the Julian Day (JD) for a given datetime.

        The Julian Day is the number of days elapsed since January 1, 4713 BC
        at noon in Universal Time. Precision: to the nearest second.

        Args:
            dte (datetime): Date and time in Universal Time (UT).

        Returns:
            float: Julian Day corresponding to the datetime.

        Reference: Meeus, chap. 7.
        """
        y, m, d = dte.year, dte.month, dte.day
        h, mn, s = dte.hour, dte.minute, dte.second
        if m <= 2:
            y -= 1
            m += 12
        a = math.floor(y / 100)
        b = 2 - a + math.floor(a / 4)
        frac_day = d + (h / 24.0) + (mn / 1440.0) + (s / 86400.0)
        return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + frac_day + b - 1524.5

    @classmethod
    def julian_century_j2000(cls, dte):
        """
        Calculates the time in Julian centuries since J2000.0 (January 1.5, 2000, JD 2451545.0).

        This parameter T is used as a variable in most of Meeus's polynomial series.

        Args:
            dte (datetime): Date and time in Universal Time.

        Returns:
            float: Number of Julian centuries since J2000.0.
        """
        return (cls.julian_day(dte) - 2451545.0) / 36525.0

    @classmethod
    def sun_position(cls, t):
        """
        Calculates the geocentric ecliptic longitude and distance of the Sun.

        Uses Meeus's low-precision series (precision ~0.01°),
        sufficient for visual observation applications.

        Args:
            t (float): Julian centuries since J2000.0 (via julian_century_j2000).

        Returns:
            tuple[float, float]:
                - l (float): Apparent ecliptic longitude of the Sun, in degrees [0, 360[.
                - r (float): Earth-Sun distance in Astronomical Units (AU).

        Reference: Meeus, chap. 25.
        """
        l0 = cls.mod360(280.46646 + 36000.76983 * t)
        m = cls.mod360(357.52911 + 35999.05029 * t)
        e = 0.016708634 - 0.000042037 * t
        c = (1.914602 - 0.004817 * t) * math.sin(math.radians(m)) + (0.019993 - 0.000101 * t) * math.sin(math.radians(2 * m))
        l = cls.mod360(l0 + c)
        r = 1.00014 * (1 - e**2) / (1 + e * math.cos(math.radians(m + c)))
        return l, r

    @classmethod
    def equation_of_time(cls, t):
        """
        Calculates the Equation of Time (apparent solar time − mean solar time).

        Args:
            t (float): Julian centuries since J2000.0.

        Returns:
            float: Equation of Time in minutes. Positive = Sun ahead.

        Reference: Meeus, chap. 28.
        """
        l0 = cls.mod360(280.46646 + 36000.76983 * t)
        s_l, _ = cls.sun_position(t)
        ra, _ = cls.ecliptic_to_equatorial(s_l, 0, t)
        alpha_deg = ra * 15.0
        eot_deg = l0 - 0.0057183 - alpha_deg
        eot_deg = ((eot_deg + 180) % 360) - 180
        return eot_deg * 4.0

    @classmethod
    def moon_position(cls, t):
        """
        Calculates the position of the Moon in geocentric ecliptic coordinates.

        Uses Meeus's complete series (precision ~0.01°) with periodic tables from
        chapter 47 (~60 terms in longitude/distance/latitude).

        Args:
            t (float): Julian centuries since J2000.0 (via julian_century_j2000).

        Returns:
            tuple[float, float, float]:
                - l (float): Geocentric ecliptic longitude, in degrees [0, 360[.
                - b (float): Geocentric ecliptic latitude, in degrees.
                - p (float): Horizontal equatorial parallax, in degrees
                             (used for parallax correction and apparent diameter).

        Reference: Meeus, chap. 47.
        """
        t2 = t * t
        t3 = t2 * t

        # Fundamental arguments (high precision)
        lp = cls.mod360(218.3164477 + 481267.88123421 * t
                        - 0.0015786 * t2 + t3 / 538841.0 - t2 * t2 / 65194000.0)
        d = cls.mod360(297.8501921 + 445267.1114034 * t
                       - 0.0018819 * t2 + t3 / 545868.0 - t2 * t2 / 113065000.0)
        m = cls.mod360(357.5291092 + 35999.0502909 * t
                       - 0.0001536 * t2 + t3 / 24490000.0)
        mp = cls.mod360(134.9633964 + 477198.8675055 * t
                        + 0.0087414 * t2 + t3 / 69699.0 - t2 * t2 / 14712000.0)
        f = cls.mod360(93.2720950 + 483202.0175233 * t
                       - 0.0036539 * t2 - t3 / 3526000.0 + t2 * t2 / 863310000.0)

        # Additional terms
        a1 = cls.mod360(119.75 + 131.849 * t)
        a2 = cls.mod360(53.09 + 479264.290 * t)
        a3 = cls.mod360(313.45 + 481266.484 * t)

        # Earth orbit eccentricity factor
        e = 1.0 - 0.002516 * t - 0.0000074 * t2

        dr = math.radians
        d_r, m_r, mp_r, f_r = dr(d), dr(m), dr(mp), dr(f)

        # Sum of periodic terms
        sl = 0.0  # longitude (micro-degrees)
        sr = 0.0  # distance (milli-km)
        sb = 0.0  # latitude (micro-degrees)

        for cD, cM, cMp, cF, amp in _MOON_LONGITUDE_TERMS:
            if amp == 0:
                continue
            arg = cD * d_r + cM * m_r + cMp * mp_r + cF * f_r
            ec = e ** abs(cM) if cM != 0 else 1.0
            sl += amp * ec * math.sin(arg)

        for cD, cM, cMp, cF, amp in _MOON_DISTANCE_TERMS:
            if amp == 0:
                continue
            arg = cD * d_r + cM * m_r + cMp * mp_r + cF * f_r
            ec = e ** abs(cM) if cM != 0 else 1.0
            sr += amp * ec * math.cos(arg)

        for cD, cM, cMp, cF, amp in _MOON_LATITUDE_TERMS:
            if amp == 0:
                continue
            arg = cD * d_r + cM * m_r + cMp * mp_r + cF * f_r
            ec = e ** abs(cM) if cM != 0 else 1.0
            sb += amp * ec * math.sin(arg)

        # Additional corrections (Meeus p.338)
        sl += 3958 * math.sin(dr(a1)) + 1962 * math.sin(dr(lp - f)) + 318 * math.sin(dr(a2))
        sb += (-2235 * math.sin(dr(lp)) + 382 * math.sin(dr(a3))
               + 175 * math.sin(dr(a1 - f)) + 175 * math.sin(dr(a1 + f))
               + 127 * math.sin(dr(lp - mp)) - 115 * math.sin(dr(lp + mp)))

        lon = cls.mod360(lp + sl / 1_000_000.0)
        lat = sb / 1_000_000.0
        dist_km = 385000.56 + sr / 1000.0
        parallax = math.degrees(math.asin(6378.14 / dist_km))

        return lon, lat, parallax

    @classmethod
    def ecliptic_to_equatorial(cls, l_deg, b_deg, t):
        """
        Converts ecliptic coordinates to equatorial coordinates.

        The transformation accounts for the obliquity of the ecliptic,
        which varies slowly with time (precession).

        Args:
            l_deg (float): Ecliptic longitude in degrees.
            b_deg (float): Ecliptic latitude in degrees.
            t (float): Julian centuries since J2000.0.

        Returns:
            tuple[float, float]:
                - ra (float): Right Ascension in decimal hours [0, 24[.
                - dec (float): Declination in degrees [-90, +90].

        Reference: Meeus, chap. 13.
        """
        eps = math.radians(23.4392911 - (46.815 * t) / 3600.0)
        l, b = math.radians(l_deg), math.radians(b_deg)
        ra = math.atan2(math.sin(l) * math.cos(eps) - math.tan(b) * math.sin(eps), math.cos(l))
        dec = math.asin(math.sin(b) * math.cos(eps) + math.cos(b) * math.sin(eps) * math.sin(l))
        return cls.mod360(math.degrees(ra)) / 15.0, math.degrees(dec)

    @classmethod
    def equatorial_to_horizontal(cls, jd, lat, lon, ra_h, dec_deg):
        """
        Converts equatorial coordinates to local horizontal coordinates.

        First calculates the Local Sidereal Time (LST) from the Julian Day
        and observer's geographic coordinates.

        Args:
            jd (float): Julian Day of the observation instant.
            lat (float): Observer's latitude in degrees (+ = North).
            lon (float): Observer's longitude in degrees (+ = East).
            ra_h (float): Right Ascension of the celestial object in decimal hours.
            dec_deg (float): Declination of the celestial object in degrees.

        Returns:
            tuple[float, float]:
                - altitude (float): Height above horizon in degrees [-90, +90].
                - azimuth (float): Azimuth in degrees [0, 360[, measured from North towards East.

        Reference: Meeus, chap. 13.
        """
        theta0 = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
        lst = cls.mod360(theta0 + lon)
        tau = math.radians(lst - ra_h * 15.0)
        phi, delta = math.radians(lat), math.radians(dec_deg)

        h = math.asin(math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(tau))
        y = -math.sin(tau)
        x = math.cos(phi) * math.tan(delta) - math.sin(phi) * math.cos(tau)
        az = cls.mod360(math.degrees(math.atan2(y, x)))
        return math.degrees(h), az

    @staticmethod
    def elevation_correction(h_true, parallax_deg):
        """
        Corrects the geometric altitude of a celestial object for atmospheric
        refraction and parallax.

        - Refraction: Bennett's formula, precision ~0.07' for h > 5°.
        - Parallax: subtracted (the Moon is significantly lower than it appears
          geometrically due to parallax).

        Args:
            h_true (float): Geometric altitude (uncorrected) in degrees.
            parallax_deg (float): Horizontal equatorial parallax in degrees
                                  (0 for the Sun, ~0.95° for the Moon).

        Returns:
            float: Corrected altitude (refraction + parallax) in degrees.

        Reference: Meeus, chap. 16.
        """
        if h_true < -5.0:
            return h_true - parallax_deg
        r = (1.02 / math.tan(math.radians(h_true + _REFRACTION_A / (h_true + _REFRACTION_B)))) / 60.0
        return h_true + r - parallax_deg

    @classmethod
    def find_events(cls, dte_ref, lat, lon, body="sun"):
        """
        Detects daily events of a celestial body by scanning minute by minute.

        Scans all 1440 minutes of the day and detects crossings of characteristic
        altitude thresholds. Temporal resolution is one minute.

        Detected thresholds:
        - Sun: rise/set (0° + correction 0.833°), civil, nautical and astronomical twilights.
        - Moon: rise/set (corrected altitude for refraction + parallax = 0°).

        Args:
            dte_ref (datetime): Any date-time within the day of interest.
            lat (float): Observer's latitude in degrees.
            lon (float): Observer's longitude in degrees.
            body (str): "sun" or "moon". Default: "sun".

        Returns:
            dict: Dictionary with the following keys (value is None if not detected):
                - 'rise'     (datetime): Time of rising.
                - 'set'      (datetime): Time of setting.
                - 'transit'  (datetime): Time of transit (maximum altitude).
                - 'dawn_civ' (datetime): Civil dawn — Sun at -6° (sun only).
                - 'dusk_civ' (datetime): Civil dusk — Sun at -6° (sun only).
                - 'dawn_naut'(datetime): Nautical dawn — Sun at -12° (sun only).
                - 'dusk_naut'(datetime): Nautical dusk — Sun at -12° (sun only).
                - 'dawn_astro'(datetime): Astronomical dawn — Sun at -18° (sun only).
                - 'dusk_astro'(datetime): Astronomical dusk — Sun at -18° (sun only).
        """
        events = {
            'rise': None, 'set': None, 'transit': None,
            'dawn_civ': None,  'dusk_civ': None,
            'dawn_naut': None, 'dusk_naut': None,
            'dawn_astro': None,'dusk_astro': None,
        }
        max_alt = -90
        prev_alt = None

        start_day = dte_ref.replace(hour=0, minute=0, second=0, microsecond=0)

        for m in range(1440):
            dt = start_day + timedelta(minutes=m)
            jd = cls.julian_day(dt)
            t = cls.julian_century_j2000(dt)

            if body == "sun":
                s_l, _ = cls.sun_position(t)
                ra, dec = cls.ecliptic_to_equatorial(s_l, 0, t)
                alt, _ = cls.equatorial_to_horizontal(jd, lat, lon, ra, dec)
                alt_test = alt + _HORIZON_CORRECTION_SUN
            else:
                m_l, m_b, m_p = cls.moon_position(t)
                ra, dec = cls.ecliptic_to_equatorial(m_l, m_b, t)
                alt, _ = cls.equatorial_to_horizontal(jd, lat, lon, ra, dec)
                alt_test = cls.elevation_correction(alt, m_p)

            # Search for transit
            if alt_test > max_alt:
                max_alt = alt_test
                events['transit'] = dt

            # Detection of horizon and twilight crossings
            if prev_alt is not None:
                if prev_alt < 0 and alt_test >= 0:
                    events['rise'] = dt
                elif prev_alt > 0 and alt_test <= 0:
                    events['set'] = dt

                if body == "sun":
                    if prev_alt < -6 and alt_test >= -6:
                        events['dawn_civ'] = dt
                    elif prev_alt > -6 and alt_test <= -6:
                        events['dusk_civ'] = dt

                    if prev_alt < -12 and alt_test >= -12:
                        events['dawn_naut'] = dt
                    elif prev_alt > -12 and alt_test <= -12:
                        events['dusk_naut'] = dt

                    if prev_alt < -18 and alt_test >= -18:
                        events['dawn_astro'] = dt
                    elif prev_alt > -18 and alt_test <= -18:
                        events['dusk_astro'] = dt

            prev_alt = alt_test

        return events

    @classmethod
    def planet_position(cls, t, name):
        """
        Calculates the geocentric position of a planet in equatorial coordinates.

        Uses Meeus's mean orbital elements (App. II) and Kepler's equation to
        obtain heliocentric coordinates, then subtracts Earth's position to get
        geocentric coordinates.

        Precision: ~1–2° depending on planet (sufficient for display and orrery).

        Args:
            t (float): Julian centuries since J2000.0 (via julian_century_j2000).
            name (str): Planet name — "Venus", "Mars", "Jupiter" or "Saturn".

        Returns:
            tuple[float, float, float]:
                - ra   (float): Right ascension in decimal hours [0, 24[.
                - dec  (float): Declination in degrees [-90, +90].
                - dist (float): Geocentric distance in Astronomical Units (AU).

        Reference: Meeus, chap. 33 / Appendix II.
        """
        L0, L1, a, e0, e1, i_deg, omega_deg, peri_deg = _ORBITAL_ELEMENTS[name]

        # Elements at instant t
        L   = cls.mod360(L0 + L1 * t)
        e   = e0 + e1 * t
        i   = math.radians(i_deg)
        omega = math.radians(omega_deg)
        peri  = math.radians(peri_deg)

        # Mean anomaly → solve Kepler's equation (Newton-Raphson)
        M = math.radians(cls.mod360(L - peri_deg))
        E = M
        for _ in range(50):
            dE = (M - E + e * math.sin(E)) / (1.0 - e * math.cos(E))
            E += dE
            if abs(dE) < 1e-10:
                break

        # True anomaly and heliocentric distance
        nu = 2.0 * math.atan2(
            math.sqrt(1.0 + e) * math.sin(E / 2.0),
            math.sqrt(1.0 - e) * math.cos(E / 2.0))
        r = a * (1.0 - e * math.cos(E))

        # Heliocentric ecliptic longitude (degrees)
        lam = cls.mod360(math.degrees(peri + nu))

        # Heliocentric ecliptic latitude (first-order approximation)
        beta = math.degrees(
            math.asin(math.sin(i) * math.sin(math.radians(lam) - omega)))

        # Heliocentric rectangular coordinates of planet
        lr, br = math.radians(lam), math.radians(beta)
        xp = r * math.cos(br) * math.cos(lr)
        yp = r * math.cos(br) * math.sin(lr)
        zp = r * math.sin(br)

        # Heliocentric position of Earth
        # (geocentric sun longitude + 180° = heliocentric Earth longitude)
        ls, r_earth = cls.sun_position(t)
        ls_r = math.radians(cls.mod360(ls + 180.0))
        xe = r_earth * math.cos(ls_r)
        ye = r_earth * math.sin(ls_r)
        ze = 0.0

        # Geocentric ecliptic vector
        dx, dy, dz = xp - xe, yp - ye, zp - ze
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        lam_geo  = cls.mod360(math.degrees(math.atan2(dy, dx)))
        beta_geo = math.degrees(math.atan2(dz, math.sqrt(dx * dx + dy * dy)))

        # Convert ecliptic → equatorial
        ra, dec = cls.ecliptic_to_equatorial(lam_geo, beta_geo, t)
        return ra, dec, dist

    # ──────────────────────────────────────────────────────────────────
    # ANGULAR SEPARATION, CONJUNCTIONS AND ECLIPSES
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def angular_separation(ra1_h, dec1_deg, ra2_h, dec2_deg):
        """
        Calculates the angular separation between two celestial objects.

        Args:
            ra1_h, dec1_deg: Equatorial coordinates of 1st object (hours, degrees).
            ra2_h, dec2_deg: Equatorial coordinates of 2nd object (hours, degrees).

        Returns:
            float: Angular separation in degrees [0, 180].

        Reference: Meeus, chap. 17.
        """
        ra1 = math.radians(ra1_h * 15.0)
        ra2 = math.radians(ra2_h * 15.0)
        d1 = math.radians(dec1_deg)
        d2 = math.radians(dec2_deg)
        cos_d = (math.sin(d1) * math.sin(d2)
                 + math.cos(d1) * math.cos(d2) * math.cos(ra1 - ra2))
        cos_d = max(-1.0, min(1.0, cos_d))
        return math.degrees(math.acos(cos_d))

    @classmethod
    def find_conjunctions(cls, dte_start, num_days=365):
        """
        Searches for planetary conjunctions and oppositions over a period.

        Scans day by day and detects minima of angular separation between
        celestial body pairs (< 5°) and oppositions of outer planets
        (elongation from Sun > 175°).

        Args:
            dte_start (datetime): Start date for search.
            num_days (int): Duration in days (default 365).

        Returns:
            list[dict]: List sorted by date, each dict contains:
                'date' (datetime), 'type' ('conjunction'|'opposition'),
                'bodies' (tuple[str, str]), 'separation' (float, degrees),
                'details' (str).
        """
        from datetime import datetime

        planets = ["Venus", "Mars", "Jupiter", "Saturn"]
        pairs = []
        for i, a in enumerate(planets):
            for b in planets[i + 1:]:
                pairs.append((a, b))

        conjunction_threshold = 5.0
        opposition_threshold = 175.0
        results = []

        prev_seps = {}
        prev_elongs = {}

        for day in range(num_days):
            dte = dte_start + timedelta(days=day)
            jd = cls.julian_day(dte)
            t = cls.julian_century_j2000(dte)

            s_l, _ = cls.sun_position(t)
            s_ra, s_dec = cls.ecliptic_to_equatorial(s_l, 0, t)

            positions = {}
            for pname in planets:
                ra, dec, _ = cls.planet_position(t, pname)
                positions[pname] = (ra, dec)

            # Planet-planet conjunctions
            for a, b in pairs:
                ra_a, dec_a = positions[a]
                ra_b, dec_b = positions[b]
                sep = cls.angular_separation(ra_a, dec_a, ra_b, dec_b)
                key = (a, b)
                if key in prev_seps and len(prev_seps[key]) >= 2:
                    p2, p1 = prev_seps[key]
                    if p1 < p2 and p1 < sep and p1 < conjunction_threshold:
                        results.append({
                            'date': dte - timedelta(days=1),
                            'type': 'conjunction',
                            'bodies': (a, b),
                            'separation': p1,
                            'details': f"{a} – {b} : {p1:.1f}°",
                        })
                prev_seps[key] = (prev_seps.get(key, (sep,))[-1], sep)

            # Planet-Sun conjunctions and oppositions
            for pname in planets:
                ra_p, dec_p = positions[pname]
                elong = cls.angular_separation(ra_p, dec_p, s_ra, s_dec)
                key = pname
                if key in prev_elongs and len(prev_elongs[key]) >= 2:
                    p2, p1 = prev_elongs[key]
                    # Conjunction with Sun (minimum elongation)
                    if p1 < p2 and p1 < elong and p1 < conjunction_threshold:
                        results.append({
                            'date': dte - timedelta(days=1),
                            'type': 'conjunction',
                            'bodies': (pname, 'Sun'),
                            'separation': p1,
                            'details': f"{pname} in solar conjunction: {p1:.1f}°",
                        })
                    # Opposition (maximum elongation > threshold, outer planets)
                    if (pname in ("Mars", "Jupiter", "Saturn")
                            and p1 > p2 and p1 > elong and p1 > opposition_threshold):
                        results.append({
                            'date': dte - timedelta(days=1),
                            'type': 'opposition',
                            'bodies': (pname, 'Sun'),
                            'separation': p1,
                            'details': f"{pname} in opposition: {p1:.1f}°",
                        })
                prev_elongs[key] = (prev_elongs.get(key, (elong,))[-1], elong)

        results.sort(key=lambda r: r['date'])
        return results

    @classmethod
    def _find_syzygy(cls, dte_approx, target_phase=0):
        """
        Refines the date of a syzygy (new moon or full moon).

        Args:
            dte_approx (datetime): Approximate date (±2 days).
            target_phase (float): 0 for new moon, 180 for full moon.

        Returns:
            datetime: Refined date (precision ~1 minute).
        """
        best_dt = dte_approx
        best_diff = 999.0

        # Pass 1: scan by 1h steps over ±2 days
        for h in range(-48, 49):
            dt = dte_approx + timedelta(hours=h)
            t = cls.julian_century_j2000(dt)
            s_l, _ = cls.sun_position(t)
            m_l, _, _ = cls.moon_position(t)
            phase = cls.mod360(m_l - s_l)
            diff = min(abs(phase - target_phase), 360 - abs(phase - target_phase))
            if diff < best_diff:
                best_diff = diff
                best_dt = dt

        # Pass 2: refine by 1 min steps over ±1h
        center = best_dt
        best_diff = 999.0
        for m in range(-60, 61):
            dt = center + timedelta(minutes=m)
            t = cls.julian_century_j2000(dt)
            s_l, _ = cls.sun_position(t)
            m_l, _, _ = cls.moon_position(t)
            phase = cls.mod360(m_l - s_l)
            diff = min(abs(phase - target_phase), 360 - abs(phase - target_phase))
            if diff < best_diff:
                best_diff = diff
                best_dt = dt

        return best_dt

    @classmethod
    def find_eclipses(cls, dte_start, num_months=12):
        """
        Searches for solar and lunar eclipses over a period.

        Scans each lunation for new and full moons, then checks if the Moon's
        ecliptic latitude is low enough for an eclipse to occur (Meeus thresholds, chap. 54).

        Args:
            dte_start (datetime): Start date.
            num_months (int): Number of synodic months to scan (default 12).

        Returns:
            list[dict]: List sorted by date, each dict contains:
                'date' (datetime), 'type' ('solar'|'lunar'),
                'certainty' ('certain'|'possible'|'penumbral'),
                'moon_latitude' (float, degrees),
                'details' (str).
        """
        synodic_month = 29.530588
        results = []

        for i in range(num_months):
            # New moon date
            dte_nm = dte_start + timedelta(days=i * synodic_month)
            nm = cls._find_syzygy(dte_nm, target_phase=0)

            t_nm = cls.julian_century_j2000(nm)
            _, b_nm, _ = cls.moon_position(t_nm)

            if abs(b_nm) < 1.58:
                certainty = 'certain' if abs(b_nm) < 0.90 else 'possible'
                results.append({
                    'date': nm,
                    'type': 'solar',
                    'certainty': certainty,
                    'moon_latitude': b_nm,
                    'details': (f"Solar eclipse ({certainty}) — "
                                f"Moon lat: {b_nm:+.2f}°"),
                })

            # Full moon date (~14.76 days after NM)
            dte_fm = dte_nm + timedelta(days=synodic_month / 2)
            fm = cls._find_syzygy(dte_fm, target_phase=180)

            t_fm = cls.julian_century_j2000(fm)
            _, b_fm, _ = cls.moon_position(t_fm)

            if abs(b_fm) < 1.58:
                if abs(b_fm) < 0.90:
                    certainty = 'certain'
                elif abs(b_fm) < 1.09:
                    certainty = 'penumbral'
                else:
                    certainty = 'possible'
                results.append({
                    'date': fm,
                    'type': 'lunar',
                    'certainty': certainty,
                    'moon_latitude': b_fm,
                    'details': (f"Lunar eclipse ({certainty}) — "
                                f"Moon lat: {b_fm:+.2f}°"),
                })

        results.sort(key=lambda r: r['date'])
        return results
