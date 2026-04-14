"""
WebSocket client test script.
Run the server first: python main.py
Then run this script in a separate terminal.
"""
import asyncio
import websockets
import json

async def listen_to_updates():
    uri = "ws://localhost:8000/ws"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Listening for updates...\n")
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                print(f"--- Received {data['type'].upper()} ---")
                for tech in data.get("technicians", []):
                    print(f"  [{tech['queue_position']}] {tech['name']} - {tech['status']}")
                print()
                
    except websockets.exceptions.ConnectionClosedError:
        print("Connection closed by server")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(listen_to_updates())
