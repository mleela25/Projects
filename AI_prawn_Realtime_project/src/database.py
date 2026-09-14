import sqlite3
import pandas as pd
from pathlib import Path
DB_PATH = Path(__file__).parents[1] / 'data' / 'aqua_data.db'

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    return conn

def insert_reading(timestamp, pond_id, temperature, do, ph, ammonia, feed_rate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO readings (timestamp, pond_id, temperature, do, ph, ammonia, feed_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""", (timestamp, pond_id, temperature, do, ph, ammonia, feed_rate))
    conn.commit()
    conn.close()


def migrate_schema():
    """Create new tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pond_id TEXT,
            temperature REAL,
            do REAL,
            ph REAL,
            ammonia REAL,
            feed_rate REAL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feed_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pond_id TEXT,
            date TEXT,
            feed_kg REAL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS disease_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pond_id TEXT,
            disease TEXT,
            medicine TEXT,
            dosage TEXT,
            duration INTEGER,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()


def insert_feed_record(pond_id, date, feed_kg):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feed_records (pond_id, date, feed_kg) VALUES (?, ?, ?)", (pond_id, date, feed_kg))
    conn.commit()
    conn.close()


def insert_disease_record(pond_id, disease, medicine, dosage, duration, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO disease_records (pond_id, disease, medicine, dosage, duration, date) VALUES (?, ?, ?, ?, ?, ?)", (pond_id, disease, medicine, dosage, duration, date))
    conn.commit()
    conn.close()

def get_latest_readings(pond_id=None, limit=500):
    conn = get_connection()
    if pond_id:
        df = pd.read_sql_query("SELECT * FROM readings WHERE pond_id = ? ORDER BY id DESC LIMIT {}".format(limit), conn, params=(pond_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM readings ORDER BY id DESC LIMIT {}".format(limit), conn)
    conn.close()
    if not df.empty:
        df = df.sort_values('id')
    return df
