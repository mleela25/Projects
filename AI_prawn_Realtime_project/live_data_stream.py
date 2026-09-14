"""Simulated real-time sensor data generator.
Run this in a separate terminal to continuously insert readings into the SQLite DB.
It inserts a new reading for each pond every N seconds.
Replace the random generation with MQTT subscription or hardware integration when ready.
"""
import time, random, datetime, argparse, logging
from src.database import insert_reading, migrate_schema
from src.config import PONDS

INTERVAL = 5  # seconds between insertions per pond

def generate_value(center, jitter=0.5):
    return round(random.uniform(center - jitter, center + jitter), 3)

def parse_args():
    parser = argparse.ArgumentParser(description='Simulated real-time sensor data generator')
    parser.add_argument('--interval', type=int, default=INTERVAL, help='Seconds between insertions per pond')
    parser.add_argument('--quiet', action='store_true', help='Reduce terminal output (no per-insert logs)')
    parser.add_argument('--once', action='store_true', help='Insert one cycle only and exit')
    return parser.parse_args()

def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    migrate_schema()
    logging.info('Starting simulated live data stream. Press Ctrl+C to stop.')
    try:
        while True:
            inserted = 0
            for pond in PONDS:
                timestamp = datetime.datetime.now().isoformat()
                temp = generate_value(29.0, 1.8)
                do = generate_value(5.0, 1.0)
                ph = generate_value(7.9, 0.25)
                ammonia = round(random.uniform(0.02, 0.12), 4)
                feed_rate = round(random.uniform(0.6, 1.2), 3)
                insert_reading(timestamp, pond, temp, do, ph, ammonia, feed_rate)
                inserted += 1
                if not args.quiet:
                    logging.info(f'Inserted: {timestamp} | {pond} | T={temp} DO={do} pH={ph} NH3={ammonia} feed={feed_rate}')
            if args.quiet:
                logging.warning(f'Cycle complete — inserted {inserted} records for {len(PONDS)} pond(s).')
            if args.once:
                break
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        logging.info('Live stream stopped by user.')

if __name__ == '__main__':
    main()
