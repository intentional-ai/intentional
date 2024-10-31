import asyncio
from time import sleep
import websockets


async def echo(uri):
    async with websockets.connect(uri) as websocket:
        print("Connected to server")
        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")
            await websocket.send(message)

while True:
    try:
        asyncio.run(echo("ws://localhost:8765"))
    except Exception as e:
        print(f"Error: {e}")
        sleep(1)
        continue