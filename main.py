import asyncio
import json
import subprocess
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# Configuration
ENGINE_DIR = "/Users/stevejin/Desktop/chess"
ENGINE_EXECUTABLE = "./run_bot.sh"

class EngineWrapper:
    def __init__(self):
        # Start the engine process from its own directory
        self.process = subprocess.Popen(
            [ENGINE_EXECUTABLE],
            cwd=ENGINE_DIR, # This ensures your engine finds its internal 'src' files
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Initial UCI Handshake
        self.send_command("uci")
        self._wait_for("uciok")
        self.send_command("isready")
        self._wait_for("readyok")

    def quit(self):
            """Gracefully shuts down the engine and kills the process"""
            try:
                self.send_command("quit")

                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception as e:
                print(f"Engine quit error, forcing kill: {e}")
                self.process.kill()
            finally:
                print("Cerberus Engine process cleaned up.")

    def _wait_for(self, target: str):
        """Helper to block until a specific string is seen in stdout"""
        while True:
            line = self.process.stdout.readline().strip()
            print(f"Engine Debug: {line}") # Uncomment this to see engine logs
            if target in line:
                break

    def send_command(self, command: str):
        if self.process.stdin:
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()

    async def get_best_move(self):
        """Asynchronously reads lines until it finds 'bestmove'"""
        while True:
            # We use to_thread to keep the WebSocket loop responsive
            line = await asyncio.to_thread(self.process.stdout.readline)
            line = line.strip()

            if not line:
                continue

            if line.startswith("bestmove"):
                # Format: "bestmove e2e4" -> returns "e2e4"
                return line.split()[1]

@app.websocket("/ws/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    engine = EngineWrapper()
    print(f"Cerberus Engine spawned from {ENGINE_DIR}")

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
