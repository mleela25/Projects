PONDS = ['Pond_A','Pond_B','Pond_C']
REFRESH_SECONDS = 5

# Pond areas in acres. If you have exact pond areas, update these values.
POND_AREAS = {
	'Pond_A': 0.5,  # acres (assumed)
	'Pond_B': 0.75, # acres (assumed)
	'Pond_C': 0.6,  # acres (assumed)
}

# Feeding: default percent of biomass to feed per day (e.g. 0.03 = 3% of biomass/day)
DEFAULT_FEEDING_PERCENT = 0.03

# Target dissolved oxygen (mg/L) we aim for
TARGET_DO = 5.0

# Aerator sizing heuristic: one standard aerator per ACRE_PER_AERATOR acres
# (adjust to your equipment - this is a conservative default)
ACRE_PER_AERATOR = 0.5

# Feed conversion ratio (biomass gain : feed consumed) - used if needed
DEFAULT_FCR = 1.5

# Default stocking / seed parameters
DEFAULT_STOCKING_DENSITY_PER_M2 = 20  # prawns per m^2 (example default)
DEFAULT_AVG_SEED_WEIGHT_G = 1.0       # average seed weight in grams
