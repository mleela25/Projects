import math
from .config import ACRE_PER_AERATOR, TARGET_DO

def required_fans(area_acres, per_aerator_acres=None):
    if per_aerator_acres is None:
        per_aerator_acres = ACRE_PER_AERATOR
    fans = max(1, int(math.ceil(area_acres / per_aerator_acres)))
    return fans

def fan_schedule(do_level):
    if do_level < 3.5:
        return 'Run fans 24/7 until DO stabilizes'
    if 3.5 <= do_level <= TARGET_DO:
        return 'Run fans from 20:00 to 06:00 (night cycle)'
    return 'Fans OFF (Sufficient DO)'
