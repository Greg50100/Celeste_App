"""
utils.py — Formatting Utilities for Céleste
============================================
Converts raw numeric values (decimal degrees, decimal hours,
phase angles) into readable character strings for the graphical interface.
"""

# ==========================================================
# 2. DATA FORMATTING
# ==========================================================
class Formatters:
    """Utility functions for text formatting of astronomical coordinates."""

    @staticmethod
    def hms(decimal_hours):
        """
        Converts Right Ascension from decimal hours to Hours/Minutes/Seconds format.

        Args:
            decimal_hours (float): Right Ascension in decimal hours (absolute value used).

        Returns:
            str: Formatted string, ex. "5h 34m 32.0s".
        """
        decimal_hours = abs(decimal_hours)
        h = int(decimal_hours)
        m = int((decimal_hours - h) * 60)
        s = round((decimal_hours - h - m / 60.0) * 3600.0, 1)
        if s >= 60:
            s = 0.0
            m += 1
        if m >= 60:
            m = 0
            h += 1
        return f"{h}h {m:02d}m {s:04.1f}s"

    @staticmethod
    def dms(decimal_degrees):
        """
        Converts Declination from decimal degrees to Degrees/Minutes/Seconds format.

        Args:
            decimal_degrees (float): Declination in decimal degrees (can be negative).

        Returns:
            str: Formatted string, ex. "-23° 26' 44\"".
        """
        sign = "-" if decimal_degrees < 0 else ""
        decimal_degrees = abs(decimal_degrees)
        d = int(decimal_degrees)
        m = int((decimal_degrees - d) * 60)
        s = round((decimal_degrees - d - m / 60.0) * 3600.0, 0)
        if s >= 60:
            s = 0
            m += 1
        if m >= 60:
            m = 0
            d += 1
        return f"{sign}{d}° {m:02d}' {int(s):02d}\""

    @staticmethod
    def lunar_phase(illumination, phase_angle):
        """
        Returns a textual description of lunar phase with emoji.

        The phase is determined by the phase angle (difference between
        Moon's ecliptic longitude and Sun's ecliptic longitude),
        divided into 8 sectors of 45°.

        Args:
            illumination (float): Percentage of visible face illumination [0, 100].
            phase_angle (float): Phase angle in degrees (Moon longitude − Sun longitude).

        Returns:
            str: Formatted string, ex. "73.2% 🌔 Waxing Gibbous".
        """
        norm = phase_angle % 360
        if norm < 22.5:
            return f"{illumination:.1f}% 🌑 New Moon"
        elif norm < 67.5:
            return f"{illumination:.1f}% 🌒 Waxing Crescent"
        elif norm < 112.5:
            return f"{illumination:.1f}% 🌓 First Quarter"
        elif norm < 157.5:
            return f"{illumination:.1f}% 🌔 Waxing Gibbous"
        elif norm < 202.5:
            return f"{illumination:.1f}% 🌕 Full Moon"
        elif norm < 247.5:
            return f"{illumination:.1f}% 🌖 Waning Gibbous"
        elif norm < 292.5:
            return f"{illumination:.1f}% 🌗 Last Quarter"
        elif norm < 337.5:
            return f"{illumination:.1f}% 🌘 Waning Crescent"
        else:
            return f"{illumination:.1f}% 🌑 New Moon"
