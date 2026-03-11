import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.engine import EngineWrapper
from app.core.config import settings

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Map game_id to a list of active WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}

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

    async def broadcast(self, message: dict, game_id: str, exclude: WebSocket = None):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass

manager = ConnectionManager()

@router.websocket("/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, mode: str = "bot"):
    await manager.connect(websocket, game_id)
    engine = None
    
    if mode == "bot":
        engine = EngineWrapper()
        print(f"Cerberus Engine spawned from {settings.ENGINE_DIR} for game {game_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")

            if mode == "player":
                # Relay messages to other clients in the room
                await manager.broadcast(message, game_id, exclude=websocket)
                
            elif mode == "bot":
                if msg_type == "ANNOUNCE_COLOR":
                    color = message.get("color")
                    if color == "b":
                        # Human is black, Bot is white and moves first
                        engine.send_command("position startpos")
                        engine.send_command("go movetime 1000")
                        best_move = await engine.get_best_move()
                        if best_move:
                            await websocket.send_json({
                                "type": "ENGINE_MOVE",
                                "move": best_move
                            })
                elif "move" in message and "fen" in message:
                    current_fen = message.get("fen")
                    
                    engine.send_command(f"position fen {current_fen}")
                    engine.send_command("go movetime 1000")
                    best_move = await engine.get_best_move()
                    if best_move:
                        await websocket.send_json({
                            "type": "ENGINE_MOVE",
                            "move": best_move
                        })

    except WebSocketDisconnect:
        print(f"Client disconnected from game {game_id}")
    except Exception as e:
        print(f"Error in websocket {game_id}: {e}")
    finally:
        manager.disconnect(websocket, game_id)
        if engine:
            engine.quit()
