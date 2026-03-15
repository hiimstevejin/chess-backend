# Config file
import os

class Settings:
    ENGINE_DIR: str = os.getenv("ENGINE_DIR", "/Users/stevejin/Desktop/chess")
    ENGINE_EXECUTABLE: str = os.getenv("ENGINE_EXECUTABLE", "./run_bot.sh")
    PUZZLES_DB_PATH: str = os.getenv(
        "PUZZLES_DB_PATH",
        "/root/data/puzzles.db",
    )

settings = Settings()
