from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages WebSocket connections for real-time alerts.
    Supports broadcasting to all connected users (physicians/nurses).
    """
    def __init__(self):
        # active_connections[user_id] = list of websockets
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Handle stale connections
                pass

manager = ConnectionManager()
