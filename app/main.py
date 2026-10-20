"""Play-log ingestion API for WJMAX.

The game client reports its play counts to POST /insert_playcount; the path and the request body
are the ones the client has always used.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from anyio import to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import get_settings
from app.db_session import REQUEST_THREADS, get_engine
from app.playcount import CountLogError, ReportConflict, parse_count_log, save_play_counts

log = logging.getLogger("wjmax")

# a full report (1,000 songs) is far smaller; anything bigger is refused before it is read
MAX_BODY_BYTES = 1_000_000


class PlayCountForm(BaseModel):
    # no spaces, line breaks or other control characters: the id is written to the log, where a line
    # break would let a client forge log lines
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[^\p{C}\p{Z}]+$")
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # the worker threads FastAPI runs requests in; the connection pool is sized to match
    to_thread.current_default_thread_limiter().total_tokens = REQUEST_THREADS
    yield


def create_app() -> FastAPI:
    docs = get_settings().docs
    app = FastAPI(
        title="WJMAX game server",
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
        lifespan=lifespan,
    )
    app.add_middleware(LimitBodySize, max_bytes=MAX_BODY_BYTES)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's own answer echoes the input back: up to a megabyte of count_log, or a lone surrogate
        # that cannot be encoded as UTF-8, which turned the 422 into a 500
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.post("/insert_playcount")
    def insert_playcount(form: PlayCountForm) -> PlayCountResult:
        try:
            songs = parse_count_log(form.count_log)
        except CountLogError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        report_id = form.report_id or uuid.uuid4().hex
        # The connection is taken only once the input is known to be good, and in the thread that uses
        # it. As a FastAPI dependency it was taken in one worker thread and used in another, so once every
        # thread was waiting for a connection, the requests that held one had no thread to finish in and
        # the pool timed out. The commit happens before the response is built, so a failed commit is
        # never reported as success.
        try:
            with get_engine().begin() as conn:
                result = save_play_counts(conn, form.device_id, report_id, songs)
        except ReportConflict as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
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
