import csv
import os
import re
import sqlite3
from typing import List

def sanitize_identifier(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r'\W+', '_', name)
    if name[0].isdigit():
        name = "_" + name
    return name


def infer_type(values: List[str]) -> str:
    non_empty = [v for v in values if v.strip() != ""]
    if not non_empty:
        return "TEXT"

    # Kinda gross and hacky way of testing data types
    try:
        [int(v) for v in non_empty]
        return "INTEGER"
    except ValueError:
        pass

    try:
        [float(v) for v in non_empty]
        return "REAL"
    except ValueError:
        pass

    return "TEXT"


def ingest_csv_to_sqlite(csv_path: str, db_path: str):
    """Ingest CSV into a SQLite database"""
    table_name = sanitize_identifier(os.path.splitext(os.path.basename(csv_path))[0])

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        headers = [sanitize_identifier(h) for h in reader[0]]
        rows = reader[1:]

    cols_data = list(zip(*rows)) if rows else [[] for _ in headers]
    col_types = [infer_type(col[:1000]) for col in cols_data] # Just test a buncha values to see what we think

    schema = ", ".join(
        f"{col} {ctype}" for col, ctype in zip(headers, col_types)
    )

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})")

    placeholders = ", ".join("?" for _ in headers)
    cur.executemany(
        f"INSERT INTO {table_name} VALUES ({placeholders})",
        rows
    )

    conn.commit()
    conn.close()
    print(f"Ingested {len(rows)} rows into table '{table_name}'.")

if __name__ == "__main__":
    ingest_csv_to_sqlite("./sensitive/site_totals.csv", "./sensitive/modbus_data.db")
