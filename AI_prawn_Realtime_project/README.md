AI-Powered Prawn Cultivation — Real-Time Demo
============================================

This project demonstrates a real-time-ready Streamlit dashboard for prawn/shrimp farming.
It uses an SQLite database as the ingestion point. A separate script (live_data_stream.py)
simulates sensor observations and inserts them into the DB. The Streamlit app (app_realtime.py)
reads the DB and updates plots, predictions, and alerts in real time.

How to run
----------
1. Create and activate a virtual environment (Python 3.9+ recommended)
   
   ```bash
   cd "/Users/m.leelaprathap/Downloads/seminar project/ai_prawn_realtime_project"
   python3 -m venv .venv
   source "/Users/m.leelaprathap/Downloads/seminar project/ai_prawn_realtime_project/.venv/bin/activate"
   ```

2. Install dependencies
   
   ```bash
   pip install -r requirements.txt
   ```

3. Start the simulated data generator (quiet mode recommended)
   
   ```bash
   python live_data_stream.py --quiet
   ```

4. In a new terminal (with the same venv activated), launch a dashboard
   
   - Real-time dashboard:
     ```bash
     streamlit run app_realtime.py
     ```
  

Notes
-----
- The simulated generator can be replaced with an MQTT subscriber to ingest real sensor data.
- The biomass predictor is a demo RandomForest trained on synthetic data. Replace with your domain model.
- The dashboard uses a simple sleep + rerun to approximate real-time behavior. In production, consider websockets or a pub/sub for low latency.
