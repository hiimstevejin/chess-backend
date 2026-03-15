import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter()


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.PUZZLES_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("", tags=["puzzles"])
def list_puzzles(limit: int = Query(..., ge=1, le=1000)) -> dict[str, Any]:
    try:
        with get_db_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    puzzle_id,
                    fen,
                    moves,
                    rating,
                    rating_deviation,
                    popularity,
                    nb_plays,
                    themes
                FROM puzzles
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    return {
        "count": len(rows),
        "items": [dict(row) for row in rows],
    }
