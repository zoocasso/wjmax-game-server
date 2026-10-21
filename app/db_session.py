"""Database engine and table definitions (SQLAlchemy Core).

The tables are declared here instead of reflected at import time, so the app starts even when the
database is briefly unreachable and the schema lives in the code (see schema.sql for the DDL).
"""

from functools import lru_cache

from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    DateTime,
    Engine,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.dialects import mysql

from app.config import get_settings

metadata = MetaData()


def exact_string(length: int) -> String:
    """A string compared byte for byte: on MySQL utf8mb4_0900_bin instead of the default
    utf8mb4_0900_ai_ci, which treats "GLORY" as "Glory", "Café" as "Cafe" and "ユメ" as "ゆめ".
    SQLite already compares exactly and has no such collation."""
    return String(length).with_variant(String(length, collation="utf8mb4_0900_bin"), "mysql")


user_tb = Table(
    "user_tb",
    metadata,
    Column("device_id", exact_string(64), primary_key=True),
    Column("insert_date", DateTime, nullable=False),  # first time the device was seen
    mysql_charset="utf8mb4",
)

# one row per chart: every song has CHARTS_PER_SONG consecutive keys that share its name
music_tb = Table(
    "music_tb",
    metadata,
    # the keys come from the game's song list, so they are not generated (schema.sql has no AUTO_INCREMENT)
    Column("music_key", Integer, primary_key=True, autoincrement=False),
    Column("name", exact_string(100), nullable=False, index=True),
    mysql_charset="utf8mb4",
)

# one row per report a device sends; report_id is the client's id for the report (it lets a retry
# be recognised) or a UUID the server made up when the client sent none
report_tb = Table(
    "report_tb",
    metadata,
    Column("device_id", exact_string(64), ForeignKey("user_tb.device_id"), primary_key=True),
    Column("report_id", exact_string(64), primary_key=True),
    # microseconds, so the snapshots of one device sort even when two arrive in the same second
    Column("reported_at", DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False),
    # SHA-256 of the play counts as parsed: a retry carries the same counts, another report sent
    # under the same id does not
    Column("counts_sha256", CHAR(64), nullable=False),
    mysql_charset="utf8mb4",
)

# play counts are appended as snapshots, one row per chart per report
playcount_tb = Table(
    "playcount_tb",
    metadata,
    # SQLite only auto-increments an INTEGER primary key
    Column("id", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("device_id", exact_string(64), nullable=False),
    Column("report_id", exact_string(64), nullable=False),
    Column("music_key", Integer, nullable=False),
    Column("count", Integer, nullable=False),
    ForeignKeyConstraint(["device_id", "report_id"], ["report_tb.device_id", "report_tb.report_id"]),
    Index("ix_playcount_tb_report", "device_id", "report_id"),
    mysql_charset="utf8mb4",
)


# FastAPI runs each request in one of this many worker threads (app.main sets the limit), and a request
# holds at most one connection, in the thread that runs it. The pool may open one connection per thread,
# so a request never waits for a connection.
REQUEST_THREADS = 40


def create_db_engine(url: str) -> Engine:
    # pool_pre_ping replaces connections MySQL has closed while idle; ten connections are kept open and
    # the rest are opened under load and closed again once ten are idle
    return create_engine(
        url, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=REQUEST_THREADS - 10
    )


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings().database_url)
