import sqlite3
import json
import os
import time
from config.settings import Setting

settings = Setting()

os.makedirs(settings.cache_dir, exist_ok=True)
db_path = os.path.join(settings.cache_dir, "cache.db")


def getConnection():
    connection = sqlite3.connect(db_path, timeout=30)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, created_at REAL)"
    )
    return connection


def getCache(key:str):
    connection = getConnection()
    try:
        row = connection.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    value, created_at = row
    age_in_hours = (time.time() - created_at) / 3600

    # old cache is treated as not present
    if age_in_hours > settings.cache_ttl_hours:
        return None

    return json.loads(value)


def setCache(key:str, value):
    # failed extractions come back as None, we do not want to remember those
    if value is None:
        return

    connection = getConnection()
    try:
        connection.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time())
        )
        connection.commit()
    finally:
        connection.close()