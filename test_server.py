import asyncio
import json
import random
import websockets

# List of substations to simulate
SUBSTATIONS = ["SS-101", "SS-102", "SS-103", "SS-104"]

async def generate_substation_data(sub_id: str) -> dict:
    """Return arbitrary but reasonable substation data."""
    return {
        "id": sub_id,
        "voltage_kV": 11.0 + random.uniform(-0.2, 0.2),  # around 11kV
        "current_A": random.uniform(50, 400),            # load current
        "power_MW": random.uniform(0.5, 5.0),            # power
        "online": random.choice([True, True, True, False]) # mostly True
    }

async def data_server(websocket):
    try:
        while True:
            # Generate one packet per substation
            for sub_id in SUBSTATIONS:
                data = await generate_substation_data(sub_id)
                await websocket.send(json.dumps(data))
            await asyncio.sleep(1.0)  # update every second
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    server = await websockets.serve(data_server, "127.0.0.1", 8080)
    print("Server started on ws://127.0.0.1:8080")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
