"""Play-log ingestion API for WJMAX.

The game client reports its play counts to POST /insert_playcount; the path and the request body
are the ones the client has always used.
"""

import logging
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import get_settings
from app.db_session import get_connection, get_engine
from app.playcount import CountLogError, parse_count_log, save_play_counts

log = logging.getLogger("wjmax")

DbConnection = Annotated[Connection, Depends(get_connection)]

# a full report (1,000 songs) is far smaller; anything bigger is refused before it is read
MAX_BODY_BYTES = 1_000_000


class PlayCountForm(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    count_log: str = Field(max_length=200_000)
    # optional: a client that sends the same id when it retries a report gets it stored only once
    report_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class PlayCountResult(BaseModel):
    saved: int
    unknown_titles: list[str]
    report_id: str
    # true when this report id was already stored for the device; nothing new was written
    duplicate: bool


class LimitBodySize:
    """ASGI middleware that answers 413 once a request body passes max_bytes.

    A declared Content-Length is checked before anything is read; a chunked body is counted as it
    arrives and the request fails as soon as it is over the limit.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_bytes):
            response = JSONResponse({"detail": "request body too large"}, status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # raised inside the endpoint's body read, so FastAPI turns it into the response
                    raise HTTPException(status_code=413, detail="request body too large")
            return message

        await self.app(scope, limited_receive, send)


def create_app() -> FastAPI:
    docs = get_settings().docs
    app = FastAPI(
        title="WJMAX game server",
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.add_middleware(LimitBodySize, max_bytes=MAX_BODY_BYTES)

    @app.post("/insert_playcount")
    def insert_playcount(form: PlayCountForm, conn: DbConnection) -> PlayCountResult:
        try:
            songs = parse_count_log(form.count_log)
        except CountLogError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        report_id = form.report_id or uuid.uuid4().hex
        # committed here, before the response is built, so a failed commit is never reported as success
        with conn.begin():
            result = save_play_counts(conn, form.device_id, report_id, songs)
        if result.unknown_titles and not result.duplicate:
            log.warning("unknown titles from %s: %s", form.device_id, result.unknown_titles)
        return PlayCountResult(
            saved=result.saved,
            unknown_titles=result.unknown_titles,
            report_id=report_id,
            duplicate=result.duplicate,
        )

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
