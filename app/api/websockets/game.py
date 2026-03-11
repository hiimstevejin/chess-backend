import json
import subprocess
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.engine import EngineWrapper
from app.core.config import settings

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps game_id to a list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast_to_others(self, message: dict, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                if connection != websocket:
                    await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, mode: str = "bot"):
    if mode == "player":
        await manager.connect(websocket, game_id)
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Broadcast move to the other player
                if message.get("move"):
                    await manager.broadcast_to_others({
                        "type": "ENGINE_MOVE", # Reuse ENGINE_MOVE for opponent moves
                        "move": message.get("move")
                    }, websocket, game_id)
                elif message.get("type") == "RESET":
                    await manager.broadcast_to_others({
                        "type": "RESET"
                    }, websocket, game_id)

        except WebSocketDisconnect:
            print(f"Closing player connection for {game_id}")
            manager.disconnect(websocket, game_id)
    else:
        # Default to bot mode
        await websocket.accept()
        engine = EngineWrapper()
        print(f"Cerberus Engine spawned from {settings.ENGINE_DIR}")

        try:
            while True:
                # 1. Receive move from React Frontend
                data = await websocket.receive_text()
                message = json.loads(data)

                # Use UCI format (e.g., 'e2e4') and the current board FEN
                user_move = message.get("move")
                current_fen = message.get("fen")

                if user_move and current_fen:
                    # 2. Update Engine state
                    engine.send_command(f"position fen {current_fen}")

                    # 3. Request Search (1 second limit)
                    engine.send_command("go movetime 1000")

                    # 4. Await response
                    best_move = await engine.get_best_move()

                    # 5. Send back to Frontend
                    await websocket.send_json({
                        "type": "ENGINE_MOVE",
                        "move": best_move
                    })

        except WebSocketDisconnect:
            print(f"Closing bot connection for {game_id}")
            engine.quit()
        finally:
            # Crucial: Kill the engine process so you don't have "zombie" engines
            engine.process.terminate()
            try:
                engine.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                engine.process.kill()
