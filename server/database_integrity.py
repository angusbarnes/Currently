import sqlite3
from datetime import datetime, timedelta

DB_PATH = "../sensitive/modbus_data.db"

def ensure_integrity(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT device_name FROM modbus_logs;")
    devices = [row[0] for row in cur.fetchall()]

    for device in devices:
        cur.execute("""
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM modbus_logs 
            WHERE device_name = ?;
        """, (device,))
        min_ts, max_ts = cur.fetchone()

        if not min_ts or not max_ts:
            continue

        start = datetime.strptime(min_ts, "%Y-%m-%d %H:%M:%S")
        end   = datetime.strptime(max_ts, "%Y-%m-%d %H:%M:%S")

        current = start
        missing = []

        while current <= end:
            ts_str = current.strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                SELECT 1 FROM modbus_logs 
                WHERE device_name = ? AND timestamp = ?;
            """, (device, ts_str))
            if not cur.fetchone():
                missing.append((ts_str, device))
            current += timedelta(minutes=15)

        if missing:
            print(f"{device}: inserting {len(missing)} missing rows")
            cur.executemany("""
                INSERT OR IGNORE INTO modbus_logs (
                    timestamp, device_name,
                    current_a, current_b, current_c,
                    power_active, power_reactive, power_apparent, power_factor,
                    voltage_an, voltage_bn, voltage_cn,
                    voltage_ab, voltage_bc, voltage_ca,
                    cumulative_active_energy
                )
                VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL, NULL);
            """, missing)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    ensure_integrity()
