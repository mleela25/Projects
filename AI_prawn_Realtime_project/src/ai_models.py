import pickle
import numpy as np
from pathlib import Path
MODEL_PATH = Path(__file__).parents[1] / 'models' / 'biomass_predictor.pkl'


class FallbackModel:
    """Simple fallback model used when the pickled model cannot be loaded.

    The predict method returns a small estimate proportional to feed_rate so
    the dashboard can continue showing reasonable numbers instead of crashing.
    """
    def predict(self, X):
        try:
            feed = float(X[0][3]) if len(X[0]) > 3 else 0.0
            return np.array([max(0.0, feed * 8.0)])
        except Exception:
            return np.array([0.0])


def load_model():
    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        return model
    except Exception as e:
        # Print warning and return fallback model
        print(f"Warning: failed to load model from {MODEL_PATH}: {e}")
        return FallbackModel()


def predict_biomass(model, temperature, do, ammonia, feed_rate):
    X = np.array([[temperature, do, ammonia, feed_rate]])
    try:
        return float(model.predict(X)[0])
    except Exception:
        # fallback heuristic
        return float(max(0.0, feed_rate * 8.0))
