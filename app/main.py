"""Play-log ingestion API for WJMAX.

The game client reports its play counts to POST /insert_playcount; the path and the request body
are the ones the client has always used.
"""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import get_settings
from app.db_session import get_connection, get_engine
from app.playcount import CountLogError, parse_count_log, save_play_counts

log = logging.getLogger("wjmax")

DbConnection = Annotated[Connection, Depends(get_connection)]


class PlayCountForm(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    count_log: str = Field(max_length=200_000)


class PlayCountResult(BaseModel):
    saved: int
    unknown_titles: list[str]


def create_app() -> FastAPI:
    docs = get_settings().docs
    app = FastAPI(
        title="WJMAX game server",
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )

    @app.post("/insert_playcount")
    def insert_playcount(form: PlayCountForm, conn: DbConnection) -> PlayCountResult:
        try:
            songs = parse_count_log(form.count_log)
        except CountLogError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        # committed here, before the response is built, so a failed commit is never reported as success
        with conn.begin():
            saved, unknown = save_play_counts(conn, form.device_id, songs)
        if unknown:
            log.warning("unknown titles from %s: %s", form.device_id, unknown)
        return PlayCountResult(saved=saved, unknown_titles=unknown)

    @app.get("/healthz")
    def healthz() -> dict:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            log.error("database check failed: %s", e)
            raise HTTPException(status_code=503, detail="database unavailable") from e
        return {"status": "ok"}

    return app


app = create_app()
