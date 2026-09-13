"""SQLite storage. All SQL values are parameterized; connections are short-lived."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def connect():
    path = Path(os.getenv('DATABASE_PATH', 'data/solar.db'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS provinces(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS districts(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
          province_id INTEGER NOT NULL REFERENCES provinces(id));
        CREATE TABLE IF NOT EXISTS substations(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
          district_id INTEGER NOT NULL REFERENCES districts(id));
        CREATE TABLE IF NOT EXISTS installations(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
          meter_id TEXT NOT NULL UNIQUE, capacity_kw REAL NOT NULL CHECK(capacity_kw>0),
          substation_id INTEGER NOT NULL REFERENCES substations(id),
          token_hash TEXT NOT NULL UNIQUE, version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY,
          installation_id INTEGER NOT NULL REFERENCES installations(id) ON DELETE RESTRICT,
          timestamp TEXT NOT NULL, power_kw REAL NOT NULL CHECK(power_kw>=0),
          energy_kwh REAL NOT NULL CHECK(energy_kwh>=0), voltage REAL NOT NULL CHECK(voltage>0),
          UNIQUE(installation_id,timestamp));
        CREATE INDEX IF NOT EXISTS readings_time ON readings(timestamp,installation_id);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('national','province','district')),
          province_id INTEGER REFERENCES provinces(id), district_id INTEGER REFERENCES districts(id),
          token_hash TEXT NOT NULL UNIQUE,
          CHECK((role='national' AND province_id IS NULL AND district_id IS NULL) OR
                (role='province' AND province_id IS NOT NULL AND district_id IS NULL) OR
                (role='district' AND district_id IS NOT NULL AND province_id IS NULL)));
        CREATE TRIGGER IF NOT EXISTS readings_no_update BEFORE UPDATE ON readings
          BEGIN SELECT RAISE(ABORT,'readings are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS readings_no_delete BEFORE DELETE ON readings
          BEGIN SELECT RAISE(ABORT,'readings are append-only'); END;
        ''')
