import pandas as pd
import numpy as np
from .config import POND_AREAS, DEFAULT_FEEDING_PERCENT, TARGET_DO, ACRE_PER_AERATOR, DEFAULT_FCR

def rolling_means(df, cols, window=6):
    res = df.copy()
    for c in cols:
        res[c + f'_roll_{window}'] = res[c].rolling(window=window, min_periods=1).mean()
    return res


def estimate_daily_feed(pond_id, biomass_kg, feeding_percent=None):
    """Estimate daily feed (kg/day) for a pond given total biomass (kg).

    Inputs:
      - pond_id: str, used only to sanity-check area
      - biomass_kg: float, current estimated biomass in pond (kg)
      - feeding_percent: fraction of biomass to feed per day (defaults to config)

    Returns: kg_feed_per_day (float), feed_per_acre (kg/acre/day)
    """
    if feeding_percent is None:
        feeding_percent = DEFAULT_FEEDING_PERCENT
    kg_per_day = biomass_kg * feeding_percent
    area = POND_AREAS.get(pond_id, 0.5)
    per_acre = kg_per_day / area if area > 0 else kg_per_day
    return float(kg_per_day), float(per_acre)


def estimate_aeration_requirements(pond_id, current_do):
    """Return recommended number of aerators and suggested runtime (hrs/day).

    Simple heuristic:
      - If DO < TARGET_DO, run aerators longer. Base runtime is 8 hrs/day.
      - Number of aerators = ceil(area / ACRE_PER_AERATOR)
    """
    area = POND_AREAS.get(pond_id, 0.5)
    aerators = int(np.ceil(area / ACRE_PER_AERATOR))
    base_runtime = 8.0
    if current_do < TARGET_DO:
        # scale runtime linearly with shortfall but cap at 24
        deficit = max(0.0, TARGET_DO - current_do)
        # assume each 1 mg/L deficit needs +2 hours per day (heuristic)
        extra = min(16.0, deficit * 2.0)
        runtime = min(24.0, base_runtime + extra)
    else:
        runtime = base_runtime
    return aerators, float(runtime)


def simple_disease_risk_score(temperature_c, do, ammonia, ph):
    """Return a 0-100 disease risk score and a short reason list.

    Heuristic factors:
      - High temperature (>30C) increases risk
      - Low DO (<3.5) increases risk
      - High ammonia (>0.12) increases risk
      - pH extremes (<7.2 or >8.5) increase risk
    """
    score = 0.0
    reasons = []
    # Temperature
    if temperature_c > 30:
        score += min(30, (temperature_c - 30) * 2)
        reasons.append('High temperature')
    elif temperature_c < 20:
        score += min(10, (20 - temperature_c))
        reasons.append('Low temperature')
    # DO
    if do < 3.5:
        score += 30
        reasons.append('Low dissolved oxygen')
    elif do < 5.0:
        score += 10
    # Ammonia
    if ammonia > 0.12:
        score += 25
        reasons.append('High ammonia')
    elif ammonia > 0.05:
        score += 8
    # pH
    if ph < 7.2 or ph > 8.5:
        score += 10
        reasons.append('pH out of range')

    score = float(min(100.0, score))
    return score, reasons


def recommend_medicine_timing(disease_risk_score):
    """Return recommendation string for medicine/treatment timing based on risk score."""
    if disease_risk_score >= 60:
        return 'High risk — initiate immediate inspection and consider treatment now. Repeat checks every 6-12 hrs.'
    elif disease_risk_score >= 30:
        return 'Moderate risk — inspect within 24 hrs, increase aeration and consider prophylactic measures. Recheck daily.'
    else:
        return 'Low risk — maintain good husbandry; monitor daily.'

