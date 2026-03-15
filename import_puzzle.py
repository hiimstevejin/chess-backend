import csv
import io
import os
import sqlite3
import zstandard as zstd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("PUZZLES_DB_PATH", str(BASE_DIR / "puzzles.db")))
CSV_ZST_PATH = Path(
    os.getenv("PUZZLES_CSV_ZST_PATH", str(BASE_DIR / "lichess_db_puzzle.csv.zst"))
)
BATCH_SIZE = 5000

def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS puzzles (
            puzzle_id TEXT PRIMARY KEY,
            fen TEXT NOT NULL,
            moves TEXT NOT NULL,
            rating INTEGER,
            rating_deviation INTEGER,
            popularity INTEGER,
            nb_plays INTEGER,
            themes TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_puzzles_rating ON puzzles(rating)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_puzzles_popularity ON puzzles(popularity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_puzzles_nb_plays ON puzzles(nb_plays)")
    conn.commit()

def to_int(value: str):
    if value is None or value == "":
        return None
    return int(value)

def insert_batch(conn: sqlite3.Connection, batch: list[tuple]) -> None:
    conn.executemany("""
        INSERT OR REPLACE INTO puzzles (
            puzzle_id,
            fen,
            moves,
            rating,
            rating_deviation,
            popularity,
            nb_plays,
            themes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    batch = []
    total = 0

    with open(CSV_ZST_PATH, "rb") as fh:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            text_reader = io.TextIOWrapper(reader, encoding="utf-8")
            csv_reader = csv.DictReader(text_reader)

            for row in csv_reader:
                batch.append((
                    row["PuzzleId"],
                    row["FEN"],
                    row["Moves"],
                    to_int(row["Rating"]),
                    to_int(row["RatingDeviation"]),
                    to_int(row["Popularity"]),
                    to_int(row["NbPlays"]),
                    row["Themes"],
                ))

                if len(batch) >= BATCH_SIZE:
                    insert_batch(conn, batch)
                    total += len(batch)
                    print(f"Inserted {total} rows...")
                    batch.clear()

    if batch:
        insert_batch(conn, batch)
        total += len(batch)

    print(f"Done. Inserted {total} rows.")
    conn.close()

if __name__ == "__main__":
    main()
