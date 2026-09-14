from datetime import datetime

def detect_disease(temp_c, ph, ammonia, do):
    # simple rule-based detector (placeholder for a trained model later)
    if ammonia > 0.12 and do < 4.0:
        return 'Gill Disease'
    elif ph > 8.5:
        return 'Shell Disease'
    elif temp_c > 32:
        return 'White Spot (Risk)'
    else:
        return 'Healthy'


def medicine_record_schema(pond_id, disease, medicine, dosage, duration):
    return {
        'pond_id': pond_id,
        'disease': disease,
        'medicine': medicine,
        'dosage': dosage,
        'duration': int(duration),
        'date': datetime.utcnow().isoformat()
    }
