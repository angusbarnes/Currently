import asyncio
import json
import sqlite3
import websockets

DB_PATH = "sensitive/modbus_data.db"   # change this to your actual file

async def stream_modbus_logs(websocket):
    """Stream modbus log rows sequentially from SQLite."""
    try:
        # open db connection (per-client safe for asyncio)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # query ordered by time and device
        cur.execute("""
            SELECT *
            FROM modbus_logs
            WHERE timestamp >= "2023-12-29 04:45:00"
            ORDER BY timestamp ASC
        """)

        batch = []
        for row in cur:
            # convert row to plain dict for JSON
            data = dict(row)
            # SQLite stores 0/1 for bools -> normalize if needed
            # e.g. if you want online/offline field, but your schema doesn't have it
            await websocket.send(json.dumps(data, default=str))

            if data["device_name"] in batch:
                print(f"Dispensed batch: {batch}")
                batch = []
                await asyncio.sleep(1.0)  # one row per second (adjust as needed)
            else:
                batch.append(data["device_name"])

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        conn.close()

async def main():
    server = await websockets.serve(stream_modbus_logs, "127.0.0.1", 8080)
    print("Server started on ws://127.0.0.1:8080")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
