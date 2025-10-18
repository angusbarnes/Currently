import sqlite3
import logging
import time
from typing import Generator, List, Dict, Any


def fetch_batches(
    db_path: str, start_time
) -> Generator[List[Dict[str, Any]], None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    cur = conn.cursor()

    cur.execute(
        "SELECT DISTINCT timestamp FROM modbus_logs WHERE timestamp >= ? ORDER BY timestamp",
        (start_time,),
    )
    timestamps = [row[0] for row in cur.fetchall()]

    for ts in timestamps:
        cur.execute("SELECT * FROM modbus_logs WHERE timestamp = ?", (ts,))
        rows = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT * FROM site_totals WHERE timestamp = ?", (ts,))
        rows.append(dict(cur.fetchone()))
        yield rows

    conn.close()


if __name__ == "__main__":
    for batch in fetch_batches("../sensitive/modbus_data.db"):
        print(batch)
        time.sleep(1)
