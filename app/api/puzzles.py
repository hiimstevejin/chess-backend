import math
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter(tags=["puzzles"])

DEFAULT_LIMIT = 24
MAX_LIMIT = 100


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.PUZZLES_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def build_rating_filters(min_rating: int | None, max_rating: int | None) -> tuple[str, list[int]]:
    clauses: list[str] = []
    params: list[int] = []

    if min_rating is not None:
        clauses.append("rating >= ?")
        params.append(min_rating)

    if max_rating is not None:
        clauses.append("rating <= ?")
        params.append(max_rating)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_clause, params


@router.get("")
def list_puzzles(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    min_rating: int | None = Query(None),
    max_rating: int | None = Query(None),
) -> dict[str, Any]:
    if min_rating is not None and max_rating is not None and min_rating > max_rating:
        raise HTTPException(
            status_code=422,
            detail="min_rating must be less than or equal to max_rating",
        )

    where_clause, filter_params = build_rating_filters(min_rating, max_rating)
    offset = (page - 1) * limit

    try:
        with get_db_connection() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM puzzles {where_clause}",
                filter_params,
            ).fetchone()

            rows = connection.execute(
                f"""
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
                {where_clause}
                ORDER BY rating ASC, puzzle_id ASC
                LIMIT ? OFFSET ?
                """,
                [*filter_params, limit, offset],
            ).fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    total = total_row["total"] if total_row is not None else 0
    total_pages = math.ceil(total / limit) if total > 0 else 0

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "filters": {
            "min_rating": min_rating,
            "max_rating": max_rating,
        },
        "count": len(rows),
        "items": [dict(row) for row in rows],
    }


@router.get("/meta")
def get_puzzles_meta() -> dict[str, Any]:
    try:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    MIN(rating) AS min_rating,
                    MAX(rating) AS max_rating
                FROM puzzles
                """
            ).fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}") from exc

    return {
        "min_rating": row["min_rating"] if row is not None else None,
        "max_rating": row["max_rating"] if row is not None else None,
        "default_limit": DEFAULT_LIMIT,
        "max_limit": MAX_LIMIT,
    }
