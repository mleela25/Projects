import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
from src.database import get_latest_readings, insert_disease_record
from src.ai_models import load_model, predict_biomass
from src.config import (
    PONDS,
    REFRESH_SECONDS,
    POND_AREAS,
    DEFAULT_STOCKING_DENSITY_PER_M2,
    DEFAULT_AVG_SEED_WEIGHT_G,
    ACRE_PER_AERATOR,
)
from src.disease_model import detect_disease
from src.utils import (
    rolling_means,
    estimate_daily_feed,
    estimate_aeration_requirements,
    simple_disease_risk_score,
    recommend_medicine_timing,
)

st.set_page_config(page_title='AI Prawn — Real-Time Dashboard', layout='wide')
st.title('AI-Powered Prawn Cultivation — Real-Time Dashboard')

# ---- Pond area overrides (persisted) ----
OVERRIDE_PATH = Path(__file__).parents[1] / 'data' / 'pond_areas_overrides.json'
STOCKING_PATH = Path(__file__).parents[1] / 'data' / 'pond_stocking.json'

def load_area_overrides():
    try:
        if OVERRIDE_PATH.exists():
            with open(OVERRIDE_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_area_overrides(mapping):
    try:
        OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OVERRIDE_PATH, 'w') as f:
            json.dump(mapping, f, indent=2)
    except Exception:
        pass

area_overrides = load_area_overrides()

# ---- Stocking dates (persisted) ----
def load_stocking_dates():
    try:
        if STOCKING_PATH.exists():
            with open(STOCKING_PATH, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_stocking_dates(mapping):
    try:
        STOCKING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STOCKING_PATH, 'w') as f:
            json.dump(mapping, f, indent=2)
    except Exception:
        pass

stocking_dates = load_stocking_dates()

model = load_model()

col1, col2 = st.columns([1,3])
with col1:
    pond = st.selectbox('Select pond', PONDS)
    st.markdown('---')
    refresh = st.slider('Auto-refresh (sec)', 5, 60, REFRESH_SECONDS)
    st.markdown('---')
    st.write('Controls')
    feed_override = st.number_input('Manual feed rate (kg/hr)', min_value=0.0, max_value=10.0, value=0.0, step=0.1)
    st.write('Note: Manual feed override is for demo; it does not change the generator behavior.')
    # Settings panel (per-run, not persisted)
    st.markdown('---')
    st.write('Settings (session only)')
    from src.config import DEFAULT_FEEDING_PERCENT, ACRE_PER_AERATOR
    feeding_percent = float(DEFAULT_FEEDING_PERCENT)  # fixed to default (control removed)
    feedings_per_day = st.selectbox('Number of feedings per day', [1,2,3,4,5,6], index=2)
    aerator_acre_override = st.number_input('Acres per aerator (override)', min_value=0.1, max_value=5.0, value=float(ACRE_PER_AERATOR), step=0.1)
    aeration_windows = st.selectbox('Aeration windows per day', [1,2,3,4], index=1)
    # Pond area override (auto-save)
    default_area = float(POND_AREAS.get(pond, 0.5))
    saved_area = float(area_overrides.get(pond, default_area))
    area_acres = st.number_input('Pond area (acres)', min_value=0.01, max_value=100.0, value=saved_area, step=0.01)
    if area_acres != saved_area:
        area_overrides[pond] = float(area_acres)
        save_area_overrides(area_overrides)
        st.caption('Saved pond area override.')
    # Show required fans and seed estimate inline in settings
    fans_required = int(max(1, round(area_acres / ACRE_PER_AERATOR)))
    area_m2_settings = area_acres * 4046.86
    seed_density_settings = float(DEFAULT_STOCKING_DENSITY_PER_M2)
    seed_count_settings = int(area_m2_settings * seed_density_settings)
    st.markdown('---')
    c_set_1, c_set_2 = st.columns(2)
    with c_set_1:
        st.write('Fans required (by acres):', fans_required)
    with c_set_2:
        st.write('Seed estimate (count):', f"{seed_count_settings:,}")
    # Stocking date (auto-save)
    import datetime as _dt
    saved_date_str = stocking_dates.get(pond)
    try:
        saved_date = _dt.date.fromisoformat(saved_date_str) if isinstance(saved_date_str, str) else _dt.date.today()
    except Exception:
        saved_date = _dt.date.today()
    stocking_date = st.date_input('Stocking date', value=saved_date, format='YYYY-MM-DD')
    if stocking_date != saved_date:
        stocking_dates[pond] = stocking_date.isoformat()
        save_stocking_dates(stocking_dates)
        st.caption('Saved stocking date.')

# auto-refresh using streamlit built-in
# use the public query_params API instead of the deprecated experimental_get_query_params
st_autorefresh = st.query_params  # used to force rerun later

df = get_latest_readings(pond_id=pond, limit=500)
if df.empty:
    st.warning('No readings found for the selected pond. Run live_data_stream.py to generate data.')
    st.stop()

latest = df.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric('Temperature (°C)', f"{latest['temperature']:.2f}")
c2.metric('Dissolved Oxygen (mg/L)', f"{latest['do']:.2f}")
c3.metric('pH', f"{latest['ph']:.2f}")
c4.metric('Ammonia (mg/L)', f"{latest['ammonia']:.4f}")

feed_val = feed_override if feed_override > 0 else float(latest['feed_rate'])
predicted = predict_biomass(model, float(latest['temperature']), float(latest['do']), float(latest['ammonia']), feed_val)

# top-level predicted biomass
st.metric('Predicted Biomass (kg)', f"{predicted:.2f}")

# Estimate feed requirements using predicted biomass and session feeding_percent
daily_feed_kg, feed_per_acre = estimate_daily_feed(pond, max(0.0, predicted), feeding_percent)

# Build feed schedule (evenly spaced times)
def build_feed_schedule(feedings, total_kg):
    if feedings <= 0:
        return []
    per_feed = total_kg / feedings
    # suggest times: spread across day starting 06:00
    start_hour = 6
    interval = int(24 / feedings)
    times = [f"{(start_hour + i*interval)%24:02d}:00" for i in range(feedings)]
    return list(zip(times, [round(per_feed, 3)]*feedings))

feed_schedule = build_feed_schedule(feedings_per_day, daily_feed_kg)

# Aeration recommendation using override for acres-per-aerator
def estimate_aeration_with_override(pond_id, current_do, acre_per_aerator_override, area_override_acres=None):
    # reuse helper but compute aerator count based on override
    area = area_override_acres if area_override_acres is not None else POND_AREAS.get(pond_id, 0.5)
    aerators = int(max(1, round(area / acre_per_aerator_override)))
    # reuse runtime heuristic from utils
    _, runtime = estimate_aeration_requirements(pond_id, current_do)
    return aerators, runtime

num_aerators, runtime_hours = estimate_aeration_with_override(pond, float(latest['do']), float(aerator_acre_override), area_override_acres=area_acres)

# Disease risk and medicine timing
risk_score, reasons = simple_disease_risk_score(float(latest['temperature']), float(latest['do']), float(latest['ammonia']), float(latest['ph']))

# Reorganize display into three panels: Feed | Aeration | Disease
col_feed, col_aero, col_disease = st.columns([1,1,1])

with col_feed:
    st.header('Feed Plan')
    st.metric('Estimated feed/day (kg)', f"{daily_feed_kg:.2f}")
    st.write(f"Feed per acre (kg/acre/day): {feed_per_acre:.2f}")
    st.write('Suggested feeding schedule:')
    for t, amt in feed_schedule:
        st.write(f"• {t} — {amt:.3f} kg")
    with st.expander('Feeding details'):
        st.write('Feeding percent used:', f"{feeding_percent:.3f} of biomass/day")
        st.write('Feed override (kg/hr):', feed_override)

with col_aero:
    st.header('Aeration')
    st.metric('Recommended aerators', f"{num_aerators}")
    st.write(f"Suggested runtime: {runtime_hours:.1f} hrs/day")
    # simple schedule split
    if runtime_hours <= 4:
        st.write('Suggested schedule: Run continuously for the suggested hours at dawn or when DO is lowest.')
    else:
        st.write('Suggested schedule: Split runtime into dawn and dusk periods to maximise oxygenation when prawns are most active.')
    # Build aeration schedule similar to feed timings
    def build_aeration_schedule(windows, total_hours):
        if windows <= 0 or total_hours <= 0:
            return []
        per = total_hours / windows
        # preferred anchors for windows: dawn 04:00, dusk 18:00, midnight 00:00, noon 12:00
        anchors = ['04:00','18:00','00:00','12:00']
        starts = anchors[:windows]
        return [(s, round(per, 1)) for s in starts]
    aero_schedule = build_aeration_schedule(int(aeration_windows), float(runtime_hours))
    if aero_schedule:
        st.write('Aeration schedule:')
        for start, hrs in aero_schedule:
            st.write(f"• {start} — run {hrs:.1f} hr(s)")
    with st.expander('Aeration details'):
        st.write('Acres per aerator used:', f"{float(aerator_acre_override):.2f}")
        st.write('Current DO:', f"{float(latest['do']):.2f} mg/L")
    # also show aerators by default rule without override
    default_aerators = int(max(1, round(area_acres / ACRE_PER_AERATOR)))
    st.caption(f"Default rule suggests {default_aerators} aerator(s) for {area_acres:.2f} acres.")

with col_disease:
    st.header('Disease Risk')
    # display colored status
    if risk_score >= 60:
        st.error(f'High risk: {risk_score:.1f}/100')
    elif risk_score >= 30:
        st.warning(f'Moderate risk: {risk_score:.1f}/100')
    else:
        st.success(f'Low risk: {risk_score:.1f}/100')
    if reasons:
        st.write('Contributing factors: ' + ', '.join(reasons))
    st.write(recommend_medicine_timing(risk_score))
    # auto disease detection + simple medicine suggestion
    disease = detect_disease(float(latest['temperature']), float(latest['ph']), float(latest['ammonia']), float(latest['do']))
    if disease != 'Healthy':
        st.warning(f"Detected condition: {disease}")
        # simple mapping for demo purposes
        med_map = {
            'Gill Disease': {'medicine': 'Potassium permanganate', 'dosage': '2-4 mg/L (pond water) or as advised', 'duration_days': 1},
            'Shell Disease': {'medicine': 'Lime (CaCO3)', 'dosage': '100-200 kg/acre, split doses', 'duration_days': 1},
            'White Spot (Risk)': {'medicine': 'Broad-spectrum immunostimulant', 'dosage': 'As per label (feed mix)', 'duration_days': 5},
        }
        plan = med_map.get(disease, {'medicine': 'Consult veterinarian', 'dosage': '—', 'duration_days': 3})
        st.write(f"Suggested medicine: {plan['medicine']}")
        st.write(f"Suggested dosage: {plan['dosage']}")
        st.write(f"Suggested duration: {plan['duration_days']} day(s)")
        with st.expander('Save treatment plan'):
            med_name = st.text_input('Medicine name', value=plan['medicine'])
            dosage = st.text_input('Dosage', value=plan['dosage'])
            duration = st.number_input('Duration (days)', min_value=1, max_value=60, value=int(plan['duration_days']))
            if st.button('Save Plan'):
                try:
                    insert_disease_record(pond, disease, med_name, dosage, int(duration), pd.Timestamp.utcnow().isoformat())
                    st.success('Treatment plan saved')
                except Exception as e:
                    st.error(f'Failed to save plan: {e}')
        st.markdown('**Immediate actions:**')
        if latest['do'] < 4.0:
            st.write('- Increase aeration to improve DO levels.')
        if latest['ammonia'] > 0.12:
            st.write('- Consider partial water exchange to dilute ammonia.')
        st.write('- Reduce feed temporarily and monitor behavior closely.')

# Alerts and emergencies
alerts = []
emergencies = []
if latest['do'] < 3.0:
    emergencies.append('EMERGENCY: DO critically low (<3.0 mg/L) — start aeration immediately.')
elif latest['do'] < 3.5:
    alerts.append('Low dissolved oxygen — consider aeration.')
if latest['ammonia'] > 0.20:
    emergencies.append('EMERGENCY: Ammonia very high (>0.20 mg/L) — perform partial water exchange.')
elif latest['ammonia'] > 0.12:
    alerts.append('High ammonia — consider partial water exchange.')
if latest['ph'] < 7.0 or latest['ph'] > 9.0:
    emergencies.append('EMERGENCY: pH far outside optimal range — take corrective action.')
elif latest['ph'] < 7.2 or latest['ph'] > 8.5:
    alerts.append('pH slightly out of optimal range.')
if latest['temperature'] > 32.0:
    alerts.append('High temperature — monitor DO and reduce feeding if needed.')

if emergencies:
    for e in emergencies:
        st.error(e)
if alerts and not emergencies:
    for a in alerts:
        st.warning(a)
if not alerts and not emergencies:
    st.success('No immediate alerts detected.')

# Water quality summary
st.subheader('Water Quality Summary')
def status(val, low, high, warn_low=None, warn_high=None):
    if warn_low is None:
        warn_low = low
    if warn_high is None:
        warn_high = high
    if val < low or val > high:
        return 'Critical'
    if val < warn_low or val > warn_high:
        return 'Watch'
    return 'Good'

temp_status = status(float(latest['temperature']), 20.0, 32.0)
do_status = status(float(latest['do']), 3.5, 8.0, warn_low=5.0, warn_high=8.0)
ph_status = status(float(latest['ph']), 7.2, 8.5, warn_low=7.3, warn_high=8.4)
nh3_status = status(float(latest['ammonia']), 0.0, 0.12, warn_low=0.0, warn_high=0.10)

st.write(f"Temperature: {temp_status}")
st.write(f"Dissolved Oxygen: {do_status}")
st.write(f"pH: {ph_status}")
st.write(f"Ammonia: {nh3_status}")

# Stocking & seed plan
st.subheader('Stocking & Seed Plan')
area_m2 = area_acres * 4046.86
seed_density = float(DEFAULT_STOCKING_DENSITY_PER_M2)
seed_count = int(area_m2 * seed_density)
avg_seed_weight_g = float(DEFAULT_AVG_SEED_WEIGHT_G)
total_seed_weight_kg = (seed_count * avg_seed_weight_g) / 1000.0
st.write(f"Recommended stocking density: {seed_density:.1f} prawn/m²")
st.write(f"Estimated pond area: {area_acres:.2f} acres ({area_m2:.0f} m²)")
seeds_per_acre = int(4046.86 * seed_density)
st.write(f"Recommended seed per acre: {seeds_per_acre:,} prawn/acre")
st.write(f"Recommended seed count: {seed_count:,}")
st.write(f"Approximate total seed weight: {total_seed_weight_kg:.1f} kg")

# Cultivation & Growth
st.subheader('Cultivation & Growth')
now_date = pd.Timestamp.utcnow().date()
try:
    days_in_culture = (now_date - stocking_date).days
except Exception:
    days_in_culture = 0
st.write(f"Days in culture (from stocking): {int(days_in_culture)} day(s)")

# Estimate average individual weight from predicted biomass and seed count
avg_weight_now_g = 0.0
if seed_count > 0:
    avg_weight_now_g = (predicted * 1000.0) / seed_count
st.write(f"Estimated average weight now: {avg_weight_now_g:.1f} g")

# Simple growth rate estimate since stocking
daily_growth_g = 0.0
if days_in_culture > 0:
    daily_growth_g = max(0.0, (avg_weight_now_g - float(DEFAULT_AVG_SEED_WEIGHT_G)) / days_in_culture)
st.write(f"Estimated daily growth: {daily_growth_g:.2f} g/day")

# Simple harvest ETA to target weight
TARGET_HARVEST_G = 25.0
eta_days = None
if daily_growth_g > 0.0 and avg_weight_now_g < TARGET_HARVEST_G:
    eta_days = int((TARGET_HARVEST_G - avg_weight_now_g) / daily_growth_g)
if eta_days is not None:
    st.info(f"Estimated days to reach {TARGET_HARVEST_G:.0f} g: ~{eta_days} day(s)")

st.subheader('Sensor Trends — last readings')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
# Select how much history to show; default to All
trend_range = st.selectbox('Trend range', ['All', 100, 200, 500], index=0)
df_plot = df if trend_range == 'All' else df.tail(int(trend_range))
fig = px.line(df_plot[['temperature','do','ph','ammonia']], labels={'value':'Measurement','timestamp':'Time'})
st.plotly_chart(fig, use_container_width=True)

st.markdown('---')
st.write('Raw recent readings (last 50)')
st.dataframe(df[['pond_id','temperature','do','ph','ammonia','feed_rate']].tail(50))

# Simple auto-refresh mechanism: use st.experimental_rerun with time-based condition
import time
if st.button('Refresh now'):
    _rerun = getattr(st, 'experimental_rerun', None)
    if callable(_rerun):
        _rerun()
    else:
        st.info('Automatic rerun not available in this Streamlit build. Please refresh the page manually.')
time.sleep(refresh)
_rerun = getattr(st, 'experimental_rerun', None)
if callable(_rerun):
    _rerun()
