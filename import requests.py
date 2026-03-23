from skyfield.api import load, wgs84
from skyfield import almanac
from fpdf import FPDF
import math

# --- CONFIGURATION ---
DATE_CALCUL = "2026-03-23"
LATITUDE = 49.6337
LONGITUDE = -1.6221
ALTITUDE = 5.0

def format_ra(ra):
    h, m, s = ra.hms()
    return f"+{int(h):02d}:{int(m):02d}:{s:06.3f}"

def format_dec(dec):
    d, m, s = dec.dms()
    sign = "+" if d >= 0 and dec.radians >= 0 else "-"
    return f"{sign}{abs(int(d)):02d}:{int(m):02d}:{s:05.2f}"

def get_events(ts, eph, body, topos_wgs84, t0, t1):
    """
    topos_wgs84 doit être l'objet wgs84.latlon pur pour l'almanac.
    """
    t_rise, t_set, t_transit = "N/A", "N/A", "N/A"
    
    # Levers et Couchers
    f_rs, edges_rs = almanac.find_discrete(t0, t1, almanac.risings_and_settings(eph, body, topos_wgs84))
    for t, is_rise in zip(f_rs, edges_rs):
        time_str = t.utc_strftime('%H:%M') + " UTC"
        if is_rise:
            t_rise = time_str
        else:
            t_set = time_str

    # Culmination (Passage au méridien)
    f_tr, edges_tr = almanac.find_discrete(t0, t1, almanac.meridian_transits(eph, body, topos_wgs84))
    for t, is_transit in zip(f_tr, edges_tr):
        if is_transit == 1: 
            t_transit = t.utc_strftime('%H:%M') + " UTC"

    return t_rise, t_transit, t_set

def generate_pro_pdf():
    print("[*] Chargement du moteur céleste Skyfield (JPL DE421)...")
    eph = load('de421.bsp')
    ts = load.timescale()
    
    earth, sun, moon = eph['earth'], eph['sun'], eph['moon']
    
    # CORRECTION : Création propre du lieu pour l'almanac
    cherbourg_topos = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ALTITUDE)
    # Création du vecteur complet (Terre -> Cherbourg) pour l'observation
    cherbourg_obs = earth + cherbourg_topos
    
    # Dates de calcul (t0 à t1 pour les événements de la journée)
    t0 = ts.utc(2026, 3, 23, 0, 0, 0)
    t1 = ts.utc(2026, 3, 24, 0, 0, 0)
    # Date pour les valeurs physiques à midi
    t_12h = ts.utc(2026, 3, 23, 12, 0, 0)
    
    print("[*] Calcul des éphémérides topocentriques apparentes pour Cherbourg...")
    
    # --- SOLEIL ---
    # On utilise cherbourg_obs pour la position
    sun_app = cherbourg_obs.at(t_12h).observe(sun).apparent()
    sun_ra, sun_dec, sun_dist = sun_app.radec(epoch='date')
    # On utilise cherbourg_topos pour les événements (almanac)
    sun_rise, sun_transit, sun_set = get_events(ts, eph, sun, cherbourg_topos, t0, t1)
    sun_diam = (1392700 / sun_dist.km) * (180 / math.pi) * 60
    
    # --- LUNE ---
    moon_app = cherbourg_obs.at(t_12h).observe(moon).apparent()
    moon_ra, moon_dec, moon_dist = moon_app.radec(epoch='date')
    moon_rise, moon_transit, moon_set = get_events(ts, eph, moon, cherbourg_topos, t0, t1)
    moon_diam = (3474.8 / moon_dist.km) * (180 / math.pi) * 60
    moon_phase = almanac.phase_angle(eph, 'moon', t_12h).degrees
    
    # --- CRÉATION DU CONTENU ASCII ---
    ascii_content = f"""
======================================================================
               * B U L L E T I N   A S T R O N O M I Q U E *
======================================================================
 Lieu observe : CHERBOURG-EN-COTENTIN (Lat: {LATITUDE} N, Lon: {abs(LONGITUDE)} W)
 Date du jour : {DATE_CALCUL}
 Ref. calcul  : Moteur Skyfield (Hors-ligne) - Apparent Topocentrique
----------------------------------------------------------------------

 [ S O L E I L ]
      \\ | /       * MOUVEMENT DIURNE
    '- ( ) -'       Lever     : {sun_rise:<10} 
      / | \\         Culminat. : {sun_transit:<10} 
                    Coucher   : {sun_set:<10} 
                    
                  * DONNEES PHYSIQUES (A 12h00 UTC)
                    Ascension Droite : {format_ra(sun_ra)}
                    Declinaison      : {format_dec(sun_dec)}
                    Distance Terre   : {sun_dist.au:.16f} UA
                    Diametre appar.  : {sun_diam:.1f}'

----------------------------------------------------------------------

 [ L U N E ]
       _.._       * MOUVEMENT DIURNE
     /   a \\        Lever     : {moon_rise:<10} 
     \\  ~  /        Culminat. : {moon_transit:<10} 
       \\._/         Coucher   : {moon_set:<10} 
                    
                  * DONNEES PHYSIQUES (A 12h00 UTC)
                    Ascension Droite : {format_ra(moon_ra)}
                    Declinaison      : {format_dec(moon_dec)}
                    Distance Terre   : {moon_dist.au:.16f} UA
                    Diametre appar.  : {moon_diam:.1f}'
                    Angle de Phase   : {moon_phase:.1f} deg

======================================================================
 Generateur   : Celeste_App v_PRO (Hors-ligne & Haute Precision)
======================================================================
"""

    print("[*] Génération du fichier PDF...")
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    
    for line in ascii_content.split('\n'):
        pdf.cell(0, 5, txt=line, ln=True, align='L')
        
    filename = f"Ephemerides_Pro_Cherbourg_{DATE_CALCUL}.pdf"
    pdf.output(filename)
    print(f"\n[SUCCÈS] Terminé ! Le PDF '{filename}' est prêt.")

if __name__ == "__main__":
    generate_pro_pdf()