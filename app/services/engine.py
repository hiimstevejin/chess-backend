import asyncio
import subprocess
from app.core.config import settings

class EngineWrapper:
    def __init__(self):
        # Start the engine process from its own directory
        self.process = subprocess.Popen(
            [settings.ENGINE_EXECUTABLE],
            cwd=settings.ENGINE_DIR, # This ensures your engine finds its internal 'src' files
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
