import math
from .config import DEFAULT_FCR

def calculate_feed(area_acres, biomass_kg, fcr=None, feeding_percent=0.03):
    """Estimate daily feed (kg/day) using biomass and an FCR or feeding percent.

    If feeding_percent is provided it takes precedence. Otherwise FCR is used.
    """
    if feeding_percent is None:
        if fcr is None:
            fcr = DEFAULT_FCR
        # convert biomass gain -> feed using FCR; here we assume daily gain ~1% of biomass
        daily_gain = biomass_kg * 0.01
        feed_kg = daily_gain * fcr
    else:
        feed_kg = biomass_kg * float(feeding_percent)
    return round(float(feed_kg), 3)
