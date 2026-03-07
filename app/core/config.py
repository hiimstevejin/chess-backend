# Config file
import os

class Settings:
    ENGINE_DIR: str = os.getenv("ENGINE_DIR", "/Users/stevejin/Desktop/chess")
    ENGINE_EXECUTABLE: str = os.getenv("ENGINE_EXECUTABLE", "./run_bot.sh")

settings = Settings()
