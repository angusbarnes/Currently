import sqlite3
from datetime import datetime

def normalize_timestamps(db_path: str, table: str = "site_totals", column: str = "timestamp"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(f"SELECT rowid, {column} FROM {table}")
    rows = cur.fetchall()

    updated = 0
    skipped = 0
    for row_id, ts in rows:
        new_ts = None

        # Try old format first: d/m/Y H:M
        try:
            dt = datetime.strptime(ts, "%d/%m/%Y %H:%M")
            new_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                skipped += 1
            except ValueError:
                print(f"⚠️ Skipping unrecognized timestamp format: {ts}")
                skipped += 1

        if new_ts and new_ts != ts:
            cur.execute(f"UPDATE {table} SET {column} = ? WHERE rowid = ?", (new_ts, row_id))
            updated += 1

    conn.commit()
    conn.close()
    print(f"✅ Done. Updated {updated} rows, skipped {skipped} rows.")

if __name__ == "__main__":
    normalize_timestamps("./sensitive/modbus_data.db")
