import json
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.engine import EngineWrapper
from app.core.config import settings

router = APIRouter()

@router.websocket("/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
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
        print(f"Closing connection for {game_id}")
        engine.quit()
    finally:
        # Crucial: Kill the engine process so you don't have "zombie" engines
        engine.process.terminate()
        try:
            engine.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            engine.process.kill()
